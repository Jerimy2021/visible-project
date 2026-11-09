"""Handler de ProcesarFunction: descarga evidencia, extrae movimientos, responde.

Se invoca de forma asíncrona desde el webhook con el MensajeEntrante serializado,
o con un payload de clasificación (respuesta de botón/lista del usuario).
"""

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
from visible.application.procesar import procesar
from visible.domain.mensaje import MensajeEntrante, desde_dict

logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger("visible.procesar")

MENSAJE_CLASIFICADO = "✓ Guardado. La próxima vez lo clasifico solo."


def _crear_extractor() -> Extractor:
    if os.environ.get("EXTRACTOR", "fake") == "bedrock":
        from visible.adapters.outbound.extractor_bedrock import BedrockExtractor

        ext = BedrockExtractor()
        logger.info("extractor=bedrock modelo=%s respaldo=%s", ext.modelo, ext.respaldo)
        return ext
    logger.info("extractor=fake")
    return FakeExtractor()


def _construir_contenido(
    mensaje: MensajeEntrante, conceptos: tuple[str, ...]
) -> tuple[Contenido, str]:
    """Devuelve (contenido, evidencia_key). La key es "" para mensajes de solo texto."""
    if mensaje.medios:
        media_id, mime = mensaje.medios[0]
        datos, mime_real = MetaMediaDownloader().descargar(media_id)
        mime_final = mime_real or mime
        key = S3Evidencias().guardar(mensaje.telefono, media_id, datos, mime_final)
        return Contenido(imagen=datos, mime_type=mime_final, conceptos=conceptos), key
    return Contenido(texto=mensaje.texto, conceptos=conceptos), ""


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


def handler(event: dict, context: object) -> dict:
    idempotencia = DynamoIdempotencia()
    mensaje_id = event.get("mensaje_id", "")
    if not idempotencia.reservar(mensaje_id):
        return {"estado": "duplicado", "mensaje_id": mensaje_id}

    try:
        if event.get("clasificacion"):
            return _clasificar(event)

        mensaje = desde_dict(event)
        perfiles = DynamoPerfiles()
        perfiles.crear_si_no_existe(mensaje.telefono)
        conceptos = tuple(perfiles.conceptos(mensaje.telefono))
        contenido, evidencia_key = _construir_contenido(mensaje, conceptos)
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
