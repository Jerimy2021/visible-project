"""Handler de ProcesarFunction: descarga evidencia, extrae movimientos, responde.

Se invoca de forma asíncrona desde el webhook con el MensajeEntrante serializado.
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


def _crear_extractor() -> Extractor:
    if os.environ.get("EXTRACTOR", "fake") == "bedrock":
        from visible.adapters.outbound.extractor_bedrock import BedrockExtractor

        ext = BedrockExtractor()
        logger.info("extractor=bedrock modelo=%s respaldo=%s", ext.modelo, ext.respaldo)
        return ext
    logger.info("extractor=fake")
    return FakeExtractor()


def _construir_contenido(mensaje: MensajeEntrante) -> tuple[Contenido, str]:
    """Devuelve (contenido, evidencia_key). La key es "" para mensajes de solo texto."""
    if mensaje.medios:
        media_id, mime = mensaje.medios[0]
        datos, mime_real = MetaMediaDownloader().descargar(media_id)
        mime_final = mime_real or mime
        key = S3Evidencias().guardar(mensaje.telefono, media_id, datos, mime_final)
        return Contenido(imagen=datos, mime_type=mime_final), key
    return Contenido(texto=mensaje.texto), ""


def handler(event: dict, context: object) -> dict:
    mensaje = desde_dict(event)

    # Idempotencia: Meta reintenta; procesamos cada mensaje una sola vez.
    idempotencia = DynamoIdempotencia()
    if not idempotencia.reservar(mensaje.mensaje_id):
        return {"estado": "duplicado", "mensaje_id": mensaje.mensaje_id}

    try:
        # El perfil se crea al primer mensaje (registra el consentimiento).
        DynamoPerfiles().crear_si_no_existe(mensaje.telefono)
        contenido, evidencia_key = _construir_contenido(mensaje)
        movimientos = procesar(
            mensaje.telefono,
            contenido,
            _crear_extractor(),
            DynamoRepositorioMovimientos(),
            WhatsAppSender(),
            evidencia_key,
        )
    except Exception:
        # Libera la reserva para que el reintento async pueda reprocesar.
        idempotencia.liberar(mensaje.mensaje_id)
        raise
    return {"estado": "ok", "movimientos": len(movimientos)}
