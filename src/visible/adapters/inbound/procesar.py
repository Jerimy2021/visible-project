"""Handler de ProcesarFunction: el flujo del asistente de WhatsApp.

Se invoca de forma asíncrona desde el webhook con:
- un MensajeEntrante serializado (texto, foto o audio), o
- la respuesta a un botón o lista (`clasificacion` = id del botón).

Ids de botones/listas que entiende:
  consent|aceptar · consent|rechazar · consent|leer
  conf|ok|<lote> · conf|fix|<lote>             (después del resumen)
  clasif|<sk>|<categoria>                       (paso 1 de clasificar)
  sub|<sk>|<categoria>|<subcategoria>           (paso 2 de clasificar)
  menu|registrar · menu|resumen · menu|alcanza · menu|negocio · menu|datos
  borrar|si · borrar|no
"""

import hashlib
import logging
import os
import uuid
from decimal import Decimal

from visible.adapters.outbound.dynamo_idempotencia import DynamoIdempotencia
from visible.adapters.outbound.dynamo_movimientos import DynamoRepositorioMovimientos
from visible.adapters.outbound.dynamo_perfiles import DynamoPerfiles
from visible.adapters.outbound.extractor_fake import FakeExtractor
from visible.adapters.outbound.media import MetaMediaDownloader
from visible.adapters.outbound.s3_evidencias import S3Evidencias
from visible.adapters.outbound.whatsapp_sender import WhatsAppSender
from visible.application import intenciones as it
from visible.application.extractor import Contenido, Extractor
from visible.application.procesar import opciones_subcategoria, procesar, soles_es
from visible.domain.categorias import es_subcategoria_valida
from visible.domain.emprendedora import id_opaco, resumen_emprendedora
from visible.domain.mensaje import MensajeEntrante, desde_dict
from visible.domain.puntaje import hoy_lima

logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger("visible.procesar")

MENSAJE_CLASIFICADO = "✓ Guardado. La próxima vez lo clasifico solo."
MENSAJE_CLASIF_VIEJO = "Ese registro ya no está (lo corregiste o borraste). No cambié nada."
MENSAJE_TIPO = "¿De qué tipo fue?"
MENSAJE_CONFIRMADO = "¡Listo! Quedó guardado ✓"
MENSAJE_CORREGIR = (
    "Listo, borré lo que leí 🗑️\n"
    "Mándame la foto de nuevo (con buena luz y de frente) o escríbeme cómo es, por ejemplo:\n"
    '"vendí 3 polos a 25"'
)
MENSAJE_ACK = "📷 Recibí tu foto, la estoy leyendo…"
MENSAJE_ACK_AUDIO = "🎧 Recibí tu audio, lo estoy escuchando…"
MENSAJE_ESCUCHE = "🎧 Escuché: «{texto}»"
MENSAJE_AUDIO_NO_ENTENDI = (
    "No te entendí bien 🙏 ¿Me lo repites más cerca del celular o me lo escribes?"
)
MENSAJE_DUPLICADA = "Esta foto ya la registré el {fecha} ✓"
MENSAJE_AUDIO = (
    "Todavía no puedo escuchar audios 🙏 ¿Me lo escribes o me mandas una foto de tu cuaderno?"
)
MENSAJE_FORMATO = (
    "Por ahora leo fotos de tu cuaderno, capturas de Yape, audios y mensajes de texto 🙏"
)
MENSAJE_BIENVENIDA = (
    "¡Gracias! Ya puedes mandarme una foto de tu cuaderno, una captura de Yape, un audio "
    "o escribirme lo que vendiste y gastaste. Yo hago las cuentas ✍️"
)
MENSAJE_RECHAZO = "Entendido, no guardaré nada. Igual puedes preguntarme cómo ordenar tu negocio."
MENSAJE_SIN_SEMANA = "Aún no tengo registros de esta semana. Mándame una foto de tu cuaderno."
MENSAJE_REGISTRAR = (
    "Mándame cualquiera de estas cosas:\n"
    "📷 una foto de tu cuaderno\n"
    "💜 una captura de Yape\n"
    "🎧 un audio contándome qué vendiste o gastaste\n"
    '✍️ un texto, por ejemplo: "vendí 3 polos a 25"'
)
MENSAJE_MENU = "¿Qué quieres hacer?"
MENSAJE_BORRAR_PREGUNTA = (
    "¿Seguro? Voy a borrar todos tus registros, fotos y audios, y tu autorización. "
    "No se puede deshacer."
)
MENSAJE_BORRADO = (
    "Listo, borré {n} registros y {f} archivos (fotos y audios) ✓\n"
    "Si vuelves a escribirme, te pediré tu autorización de nuevo."
)
MENSAJE_NO_BORRAR = "Perfecto, no borré nada ✓"
AVISO_LEY_29733 = (
    "Para usar Visible necesito tu autorización para tratar tus datos personales, "
    "según la Ley N.° 29733:\n"
    "1. Qué guardo: fotos de tu cuaderno, capturas, audios, montos y fechas.\n"
    "2. Para qué: darte tu resumen y, si tú lo pides, tu evaluación de crédito.\n"
    "3. Quién lo ve: solo tú. Mibanco o Yape, solo si lo autorizas. Nada va a la SUNAT.\n"
    '4. Tus derechos: escribe "mis datos" para verlos o "borrar mis datos" para eliminarlos.\n'
    "¿Aceptas?"
)
LEER_MAS = (
    "Más detalle:\n"
    "• Tus fotos y audios se guardan cifrados en servidores de Amazon Web Services.\n"
    "• Los leemos con inteligencia artificial solo para sacar montos, fechas y conceptos.\n"
    "• No vendemos tus datos ni los mandamos a la SUNAT.\n"
    "• Mibanco o Yape solo ven tu historial si tú lo autorizas aparte.\n"
    '• Puedes ver o borrar todo cuando quieras escribiendo "mis datos" o "borrar mis datos".'
)
BOTONES_CONSENT = [
    ("consent|aceptar", "Aceptar"),
    ("consent|rechazar", "Rechazar"),
    ("consent|leer", "Leer más"),
]
OPCIONES_MENU = [
    ("menu|registrar", "📷 Registrar"),
    ("menu|resumen", "📊 Mi resumen"),
    ("menu|alcanza", "🛒 ¿Me alcanza?"),
    ("menu|negocio", "📱 Ver mi negocio"),
    ("menu|datos", "🔒 Mis datos"),
]
BOTONES_BORRAR = [("borrar|si", "Sí, borrar todo"), ("borrar|no", "No, mantener")]


def _crear_extractor() -> Extractor:
    if os.environ.get("EXTRACTOR", "fake") == "bedrock":
        from visible.adapters.outbound.extractor_bedrock import BedrockExtractor

        ext = BedrockExtractor()
        logger.info("extractor=bedrock modelo=%s respaldo=%s", ext.modelo, ext.respaldo)
        return ext
    logger.info("extractor=fake")
    return FakeExtractor()


def _transcribir_activo() -> bool:
    return os.environ.get("TRANSCRIBIR", "off").lower() in ("on", "1", "true", "si")


def _es_audio(mensaje: MensajeEntrante) -> bool:
    return bool(mensaje.medios) and mensaje.medios[0][1].startswith("audio")


def _es_imagen(mensaje: MensajeEntrante) -> bool:
    return bool(mensaje.medios) and mensaje.medios[0][1].startswith("image")


def _link_negocio(telefono: str) -> str:
    base = os.environ.get("LINK_PANEL", "")
    return f"{base}/?mi={id_opaco(telefono)}" if base else ""


# --- Botones ----------------------------------------------------------------


def _clasificar(telefono: str, partes: list[str]) -> dict:
    """Paso 1: elige categoría. Si la categoría tiene tipos, pregunta el tipo (paso 2)."""
    if len(partes) != 3:
        return {"estado": "ignorado"}
    _, sk, categoria = partes
    concepto = DynamoRepositorioMovimientos().actualizar_categoria(telefono, sk, categoria)
    sender = WhatsAppSender()
    if concepto is None:
        sender.enviar_texto(telefono, MENSAJE_CLASIF_VIEJO)
        return {"estado": "clasif_inexistente"}
    tipos = opciones_subcategoria(sk, categoria)
    if tipos:
        sender.enviar_opciones(telefono, MENSAJE_TIPO, tipos)
        return {"estado": "clasif_paso1"}
    DynamoPerfiles().aprender(telefono, concepto, categoria)
    sender.enviar_texto(telefono, MENSAJE_CLASIFICADO)
    return {"estado": "clasificado"}


def _subclasificar(telefono: str, partes: list[str]) -> dict:
    """Paso 2: guarda el tipo y aprende "concepto = categoria (tipo)"."""
    if len(partes) != 4 or not es_subcategoria_valida(partes[2], partes[3]):
        return {"estado": "ignorado"}
    _, sk, categoria, sub = partes
    concepto = DynamoRepositorioMovimientos().actualizar_categoria(telefono, sk, categoria, sub)
    sender = WhatsAppSender()
    if concepto is None:
        sender.enviar_texto(telefono, MENSAJE_CLASIF_VIEJO)
        return {"estado": "clasif_inexistente"}
    DynamoPerfiles().aprender(telefono, concepto, f"{categoria} ({sub})")
    sender.enviar_texto(telefono, MENSAJE_CLASIFICADO)
    logger.info("clasificacion sk=%s categoria=%s sub=%s", sk, categoria, sub)
    return {"estado": "clasificado"}


def _confirmar(telefono: str, partes: list[str]) -> dict:
    if len(partes) != 3:
        return {"estado": "ignorado"}
    _, accion, lote = partes
    sender = WhatsAppSender()
    if accion == "ok":
        sender.enviar_texto(telefono, MENSAJE_CONFIRMADO)
        return {"estado": "confirmado"}
    n = DynamoRepositorioMovimientos().borrar_lote(telefono, lote)
    DynamoIdempotencia().liberar_imagen_de_lote(telefono, lote)  # permite reenviar la foto
    sender.enviar_texto(telefono, MENSAJE_CORREGIR)
    logger.info("corregir lote=%s borrados=%s", lote, n)
    return {"estado": "corregido", "borrados": n}


def _consentir(telefono: str, decision: str) -> dict:
    """Respuesta a los botones del aviso Ley 29733."""
    perfiles, sender = DynamoPerfiles(), WhatsAppSender()
    if decision == "leer":
        sender.enviar_texto(telefono, LEER_MAS)
        sender.enviar_opciones(telefono, "¿Aceptas?", BOTONES_CONSENT[:2])
        return {"estado": "consentimiento_leer_mas"}
    if decision == "aceptar":
        perfiles.crear_si_no_existe(telefono)
        perfiles.aceptar_consentimiento(telefono)
        sender.enviar_texto(telefono, MENSAJE_BIENVENIDA)
        sender.enviar_opciones(telefono, MENSAJE_MENU, OPCIONES_MENU)
        return {"estado": "consentimiento_aceptado"}
    perfiles.crear_si_no_existe(telefono)
    perfiles.rechazar_consentimiento(telefono)
    sender.enviar_texto(telefono, MENSAJE_RECHAZO)
    return {"estado": "consentimiento_rechazado"}


def _menu(telefono: str, opcion: str) -> dict:
    if opcion == "registrar":
        WhatsAppSender().enviar_texto(telefono, MENSAJE_REGISTRAR)
        return {"estado": "menu_registrar"}
    if opcion == "resumen":
        return _resumen_semana(telefono)
    if opcion == "alcanza":
        return _alcanza(telefono, None)
    if opcion == "negocio":
        return _ver_negocio(telefono)
    if opcion == "datos":
        return _mis_datos(telefono)
    return {"estado": "ignorado"}


def _borrar(telefono: str, decision: str) -> dict:
    sender = WhatsAppSender()
    if decision != "si":
        sender.enviar_texto(telefono, MENSAJE_NO_BORRAR)
        return {"estado": "borrar_cancelado"}
    n = DynamoRepositorioMovimientos().borrar_todo(telefono)
    f = S3Evidencias().borrar_de(telefono)
    DynamoIdempotencia().borrar_imagenes(telefono)
    DynamoPerfiles().borrar(telefono)
    sender.enviar_texto(telefono, MENSAJE_BORRADO.format(n=n, f=f))
    logger.info("borrar_mis_datos movimientos=%s archivos=%s", n, f)
    return {"estado": "datos_borrados", "movimientos": n, "archivos": f}


def _boton(telefono: str, id_boton: str) -> dict:
    partes = id_boton.split("|")
    tipo = partes[0]
    if tipo == "consent":
        return _consentir(telefono, partes[-1])
    # Lo demás requiere consentimiento vigente.
    if DynamoPerfiles().estado_consentimiento(telefono) != "aceptado":
        WhatsAppSender().enviar_opciones(telefono, AVISO_LEY_29733, BOTONES_CONSENT)
        return {"estado": "consentimiento_pendiente"}
    if tipo == "clasif":
        return _clasificar(telefono, partes)
    if tipo == "sub":
        return _subclasificar(telefono, partes)
    if tipo == "conf":
        return _confirmar(telefono, partes)
    if tipo == "menu" and len(partes) == 2:
        return _menu(telefono, partes[1])
    if tipo == "borrar" and len(partes) == 2:
        return _borrar(telefono, partes[1])
    return {"estado": "ignorado"}


# --- Intenciones de texto ----------------------------------------------------


def _resumen_semana(telefono: str) -> dict:
    hoy = hoy_lima()
    r = resumen_emprendedora(DynamoRepositorioMovimientos().leer_ventana(telefono, hoy), hoy)
    s = r["semana"]
    if not any(s[k] for k in ("ventas", "gastos_negocio", "gastos_personales")):
        WhatsAppSender().enviar_texto(telefono, MENSAJE_SIN_SEMANA)
        return {"estado": "resumen_vacio"}

    def sol(x: float) -> str:
        return soles_es(Decimal(str(x)))

    texto = (
        "Tu semana (últimos 7 días):\n"
        f"Vendiste {sol(s['ventas'])}\n"
        f"Gastos del negocio − {sol(s['gastos_negocio'])}\n"
        f"Ganancia del negocio {sol(s['ganancia'])}\n"
        f"Gastos personales − {sol(s['gastos_personales'])}\n"
        f"Tu ahorro {sol(s['ahorro'])}"
    )
    link, sender = _link_negocio(telefono), WhatsAppSender()
    if link:
        sender.enviar_link(telefono, texto, "Ver mi negocio", link)
    else:
        sender.enviar_texto(telefono, texto)
    return {"estado": "resumen"}


def _alcanza(telefono: str, monto: Decimal | None) -> dict:
    perfiles = DynamoPerfiles()
    if monto is None:
        perfiles.esperar(telefono, "alcanza")  # su próximo mensaje con un monto responde esto
        WhatsAppSender().enviar_texto(telefono, it.responder_alcanza(None, Decimal(0), soles_es))
        return {"estado": "alcanza_pregunta"}
    perfiles.esperar(telefono, "")
    hoy = hoy_lima()
    r = resumen_emprendedora(DynamoRepositorioMovimientos().leer_ventana(telefono, hoy), hoy)
    ahorro = Decimal(str(r["semana"]["ahorro"]))
    WhatsAppSender().enviar_texto(telefono, it.responder_alcanza(monto, ahorro, soles_es))
    logger.info("alcanza monto=%s ahorro=%s", monto, ahorro)
    return {"estado": "alcanza", "monto": float(monto)}


def _ver_negocio(telefono: str) -> dict:
    link, sender = _link_negocio(telefono), WhatsAppSender()
    if link:
        sender.enviar_link(
            telefono, "Aquí ves tu ganancia, tu ahorro y tus tableros 📱", "Ver mi negocio", link
        )
    else:
        sender.enviar_texto(telefono, "Tu panel todavía no está disponible 🙏")
    return {"estado": "ver_negocio"}


def _mis_datos(telefono: str) -> dict:
    perfil = DynamoPerfiles().obtener(telefono) or {}
    n, desde = DynamoRepositorioMovimientos().contar(telefono)
    texto = (
        "🔒 Tus datos en Visible:\n"
        f"• {n} registros" + (f" desde el {desde}" if desde else "") + ", con sus fotos y audios.\n"
        f"• Autorizaste el {perfil.get('consentimiento') or '—'}.\n"
        "• Solo tú los ves. Mibanco o Yape, solo si lo autorizas.\n"
        'Para eliminar todo, escribe "borrar mis datos".'
    )
    link, sender = _link_negocio(telefono), WhatsAppSender()
    if link:
        sender.enviar_link(telefono, texto, "Ver mis registros", link)
    else:
        sender.enviar_texto(telefono, texto)
    return {"estado": "mis_datos"}


def _intencion(telefono: str, intencion: it.Intencion) -> dict | None:
    """Atiende una intención de texto. None = es un registro (va al extractor)."""
    nombre = intencion.nombre
    if nombre == it.MENU:
        WhatsAppSender().enviar_opciones(telefono, MENSAJE_MENU, OPCIONES_MENU)
        return {"estado": "menu"}
    if nombre == it.RESUMEN:
        return _resumen_semana(telefono)
    if nombre == it.ALCANZA:
        return _alcanza(telefono, intencion.monto)
    if nombre == it.NEGOCIO:
        return _ver_negocio(telefono)
    if nombre == it.MIS_DATOS:
        return _mis_datos(telefono)
    if nombre == it.BORRAR:
        WhatsAppSender().enviar_opciones(telefono, MENSAJE_BORRAR_PREGUNTA, BOTONES_BORRAR)
        return {"estado": "borrar_pregunta"}
    return None


# --- Handler -----------------------------------------------------------------


def handler(event: dict, context: object) -> dict:
    idempotencia = DynamoIdempotencia()
    mensaje_id = event.get("mensaje_id", "")
    if not idempotencia.reservar(mensaje_id):
        return {"estado": "duplicado", "mensaje_id": mensaje_id}

    try:
        if event.get("clasificacion"):
            return _boton(event.get("telefono", ""), event["clasificacion"])
        return _mensaje(desde_dict(event), idempotencia)
    except Exception:
        idempotencia.liberar(mensaje_id)
        raise


def _mensaje(mensaje: MensajeEntrante, idempotencia: DynamoIdempotencia) -> dict:
    telefono = mensaje.telefono
    perfiles, sender = DynamoPerfiles(), WhatsAppSender()
    perfiles.crear_si_no_existe(telefono)

    # Consentimiento: sin aceptar, no se procesa ni guarda nada.
    if perfiles.estado_consentimiento(telefono) != "aceptado":
        sender.enviar_opciones(telefono, AVISO_LEY_29733, BOTONES_CONSENT)
        return {"estado": "consentimiento_pendiente"}

    if not mensaje.medios and not (mensaje.texto or "").strip():
        return {"estado": "ignorado"}  # reacciones, ubicación, etc.
    if mensaje.medios and not (_es_imagen(mensaje) or _es_audio(mensaje)):
        sender.enviar_texto(telefono, MENSAJE_FORMATO)
        return {"estado": "formato_no_soportado"}
    if _es_audio(mensaje) and not _transcribir_activo():
        sender.enviar_texto(telefono, MENSAJE_AUDIO)
        return {"estado": "audio"}

    texto = mensaje.texto
    evidencia_key, sha, mime_final, datos = "", "", "", b""
    lote = uuid.uuid4().hex[:10]

    if mensaje.medios:
        sender.enviar_texto(telefono, MENSAJE_ACK_AUDIO if _es_audio(mensaje) else MENSAJE_ACK)
        media_id, mime = mensaje.medios[0]
        datos, mime_real = MetaMediaDownloader().descargar(media_id)
        mime_final = mime_real or mime
        # Antiduplicados: SHA-256 del archivo por usuaria.
        sha = hashlib.sha256(datos).hexdigest()
        previa = idempotencia.registrar_imagen(telefono, sha, hoy_lima().isoformat())
        if previa is not None:
            sender.enviar_texto(telefono, MENSAJE_DUPLICADA.format(fecha=previa))
            logger.info("archivo duplicado telefono=%s sha=%s", telefono, sha[:12])
            return {"estado": "duplicado_imagen", "fecha": previa}
        evidencia_key = S3Evidencias().guardar(telefono, media_id, datos, mime_final)
        idempotencia.registrar_lote(telefono, lote, sha)
    try:
        return _continuar(
            mensaje,
            perfiles,
            sender,
            idempotencia,
            texto,
            evidencia_key,
            lote,
            mime_final,
            datos if mensaje.medios else None,
        )
    except Exception:
        # Si algo falla después de registrar el archivo, que el reintento no lo vea duplicado.
        if sha:
            idempotencia.liberar_imagen_de_lote(telefono, lote)
        raise


def _continuar(
    mensaje, perfiles, sender, idempotencia, texto, evidencia_key, lote, mime_final, datos
) -> dict:
    telefono = mensaje.telefono
    imagen = None
    if mensaje.medios:
        if _es_audio(mensaje):
            media_id = mensaje.medios[0][0]
            from visible.adapters.outbound.transcriptor import TranscribeTranscriptor

            texto = TranscribeTranscriptor().transcribir(telefono, media_id, evidencia_key)
            if not texto:
                idempotencia.liberar_imagen_de_lote(telefono, lote)
                sender.enviar_texto(telefono, MENSAJE_AUDIO_NO_ENTENDI)
                return {"estado": "audio_sin_texto"}
            sender.enviar_texto(telefono, MENSAJE_ESCUCHE.format(texto=texto[:400]))
        else:
            imagen = datos

    # Texto (escrito o del audio): primero, ¿es una pregunta o un comando?
    if imagen is None:
        intencion = it.detectar(texto)
        # Si le preguntamos "¿para cuánto?" y responde solo un monto.
        if intencion.nombre == it.REGISTRO and perfiles.esperando(telefono) == "alcanza":
            monto = it.extraer_monto(texto)
            if monto is not None and len(texto.split()) <= 3:
                return _alcanza(telefono, monto)
        respuesta = _intencion(telefono, intencion)
        if respuesta is not None:
            return respuesta

    conceptos = tuple(perfiles.conceptos(telefono))
    if imagen is not None:
        contenido = Contenido(imagen=imagen, mime_type=mime_final, conceptos=conceptos)
    else:
        contenido = Contenido(texto=texto, conceptos=conceptos)

    extraccion = procesar(
        telefono,
        contenido,
        _crear_extractor(),
        DynamoRepositorioMovimientos(),
        sender,
        evidencia_key,
        lote=lote,
    )
    return {"estado": "ok", "movimientos": len(extraccion.movimientos)}
