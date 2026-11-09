"""Handler de ProcesarFunction: descarga evidencia, extrae movimientos, responde.

Se invoca de forma asíncrona desde el webhook con el MensajeEntrante serializado,
o con un payload de clasificación (respuesta de botón/lista del usuario).
"""

import hashlib
import logging
import os

from visible.adapters.outbound.dynamo_idempotencia import DynamoIdempotencia
from visible.adapters.outbound.dynamo_movimientos import DynamoRepositorioMovimientos
from visible.adapters.outbound.dynamo_perfiles import DynamoPerfiles
from visible.adapters.outbound.extractor_fake import FakeExtractor
from visible.adapters.outbound.media import MetaMediaDownloader
from visible.adapters.outbound.s3_evidencias import S3Evidencias
from visible.adapters.outbound.whatsapp_sender import WhatsAppSender
from visible.application.extractor import Contenido, Extractor
from visible.application.procesar import procesar, soles_es
from visible.domain.mensaje import MensajeEntrante, desde_dict
from visible.domain.puntaje import hoy_lima, totales_semana

logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger("visible.procesar")

MENSAJE_CLASIFICADO = "✓ Guardado. La próxima vez lo clasifico solo."
MENSAJE_ACK = "📷 Recibí tu foto, la estoy leyendo…"
MENSAJE_DUPLICADA = "Esta foto ya la registré el {fecha} ✓"
MENSAJE_AUDIO = (
    "Todavía no puedo escuchar audios 🙏 ¿Me lo escribes o me mandas una foto de tu cuaderno?"
)
MENSAJE_BIENVENIDA = (
    "¡Gracias! Ya puedes mandarme una foto de tu cuaderno o escribirme lo que vendiste "
    "y gastaste. Yo hago las cuentas ✍️"
)
MENSAJE_RECHAZO = "Entendido, no guardaré nada. Igual puedes preguntarme cómo ordenar tu negocio."
MENSAJE_SIN_SEMANA = "Aún no tengo registros de esta semana. Mándame una foto de tu cuaderno."
AVISO_LEY_29733 = (
    "Para usar Visible necesito tu autorización para tratar tus datos personales, "
    "según la Ley N.° 29733:\n"
    "1. Qué guardo: fotos de tu cuaderno, capturas, montos y fechas.\n"
    "2. Para qué: darte tu resumen y, si tú lo pides, tu evaluación de crédito.\n"
    "3. Quién lo ve: solo tú. Mibanco o Yape, solo si lo autorizas. Nada va a la SUNAT.\n"
    '4. Tus derechos: escribe "mis datos" para verlos o "borrar mis datos" para eliminarlos.\n'
    "¿Aceptas?"
)
BOTONES_CONSENT = [("consent|aceptar", "Aceptar"), ("consent|rechazar", "Rechazar")]
PALABRAS_RESUMEN = ("resumen", "cuánto gané", "cuanto gane", "cuanto gané", "mi semana")


def _crear_extractor() -> Extractor:
    if os.environ.get("EXTRACTOR", "fake") == "bedrock":
        from visible.adapters.outbound.extractor_bedrock import BedrockExtractor

        ext = BedrockExtractor()
        logger.info("extractor=bedrock modelo=%s respaldo=%s", ext.modelo, ext.respaldo)
        return ext
    logger.info("extractor=fake")
    return FakeExtractor()


def _es_audio(mensaje: MensajeEntrante) -> bool:
    return bool(mensaje.medios) and mensaje.medios[0][1].startswith("audio")


def _intencion_resumen(texto: str) -> bool:
    t = (texto or "").strip().lower()
    return any(p in t for p in PALABRAS_RESUMEN)


def _clasificar(event: dict) -> dict:
    """Aplica la respuesta de un botón: actualiza categoría y aprende el concepto."""
    telefono = event.get("telefono", "")
    partes = (event.get("clasificacion") or "").split("|")
    if len(partes) != 3 or partes[0] != "clasif":
        return {"estado": "ignorado"}
    _, sk, categoria = partes
    concepto = DynamoRepositorioMovimientos().actualizar_categoria(telefono, sk, categoria)
    DynamoPerfiles().aprender(telefono, concepto, categoria)
    WhatsAppSender().enviar_texto(telefono, MENSAJE_CLASIFICADO)
    logger.info("clasificacion sk=%s categoria=%s concepto=%s", sk, categoria, concepto)
    return {"estado": "clasificado"}


def _consentir(event: dict) -> dict:
    """Respuesta a los botones del aviso Ley 29733."""
    telefono = event.get("telefono", "")
    decision = (event.get("clasificacion") or "").split("|")[-1]
    perfiles = DynamoPerfiles()
    if decision == "aceptar":
        perfiles.aceptar_consentimiento(telefono)
        WhatsAppSender().enviar_texto(telefono, MENSAJE_BIENVENIDA)
        return {"estado": "consentimiento_aceptado"}
    perfiles.rechazar_consentimiento(telefono)
    WhatsAppSender().enviar_texto(telefono, MENSAJE_RECHAZO)
    return {"estado": "consentimiento_rechazado"}


def _resumen_semana(telefono: str) -> dict:
    hoy = hoy_lima()
    t = totales_semana(DynamoRepositorioMovimientos().leer_ventana(telefono, hoy), hoy)
    if not any(t[k] for k in ("ventas", "gastos_negocio", "gastos_personales")):
        WhatsAppSender().enviar_texto(telefono, MENSAJE_SIN_SEMANA)
        return {"estado": "resumen_vacio"}
    texto = (
        "Tu semana:\n"
        f"Vendiste {soles_es(t['ventas'])}\n"
        f"Gastos del negocio − {soles_es(t['gastos_negocio'])}\n"
        f"Ganancia del negocio {soles_es(t['ganancia'])}\n"
        f"Gastos personales − {soles_es(t['gastos_personales'])}"
    )
    link = os.environ.get("LINK_PANEL", "")
    sender = WhatsAppSender()
    if link:
        sender.enviar_link(telefono, texto, "Ver mi negocio", link)
    else:
        sender.enviar_texto(telefono, texto)
    return {"estado": "resumen"}


def handler(event: dict, context: object) -> dict:
    idempotencia = DynamoIdempotencia()
    mensaje_id = event.get("mensaje_id", "")
    if not idempotencia.reservar(mensaje_id):
        return {"estado": "duplicado", "mensaje_id": mensaje_id}

    try:
        clasif = event.get("clasificacion") or ""
        if clasif.startswith("consent|"):
            return _consentir(event)
        if clasif:
            return _clasificar(event)

        mensaje = desde_dict(event)

        # Audio: aún no se procesa.
        if _es_audio(mensaje):
            WhatsAppSender().enviar_texto(mensaje.telefono, MENSAJE_AUDIO)
            return {"estado": "audio"}

        perfiles = DynamoPerfiles()
        perfiles.crear_si_no_existe(mensaje.telefono)

        # Consentimiento: sin aceptar, no se procesa ni guarda nada.
        if perfiles.estado_consentimiento(mensaje.telefono) != "aceptado":
            WhatsAppSender().enviar_opciones(mensaje.telefono, AVISO_LEY_29733, BOTONES_CONSENT)
            return {"estado": "consentimiento_pendiente"}

        # Texto de resumen ("resumen", "cuánto gané", "mi semana").
        if not mensaje.medios and _intencion_resumen(mensaje.texto):
            return _resumen_semana(mensaje.telefono)

        # Acuse instantáneo antes de descargar/leer (Bedrock tarda).
        if mensaje.medios:
            WhatsAppSender().enviar_texto(mensaje.telefono, MENSAJE_ACK)
        conceptos = tuple(perfiles.conceptos(mensaje.telefono))

        evidencia_key = ""
        if mensaje.medios:
            media_id, mime = mensaje.medios[0]
            datos, mime_real = MetaMediaDownloader().descargar(media_id)
            mime_final = mime_real or mime
            # Antiduplicados: SHA-256 de la imagen por usuaria.
            sha = hashlib.sha256(datos).hexdigest()
            previa = idempotencia.registrar_imagen(mensaje.telefono, sha, hoy_lima().isoformat())
            if previa is not None:
                WhatsAppSender().enviar_texto(
                    mensaje.telefono, MENSAJE_DUPLICADA.format(fecha=previa)
                )
                logger.info("imagen duplicada telefono=%s sha=%s", mensaje.telefono, sha[:12])
                return {"estado": "duplicado_imagen", "fecha": previa}
            evidencia_key = S3Evidencias().guardar(mensaje.telefono, media_id, datos, mime_final)
            contenido = Contenido(imagen=datos, mime_type=mime_final, conceptos=conceptos)
        else:
            contenido = Contenido(texto=mensaje.texto, conceptos=conceptos)

        extraccion = procesar(
            mensaje.telefono,
            contenido,
            _crear_extractor(),
            DynamoRepositorioMovimientos(),
            WhatsAppSender(),
            evidencia_key,
        )
    except Exception:
        idempotencia.liberar(mensaje_id)
        raise
    return {"estado": "ok", "movimientos": len(extraccion.movimientos)}
