"""Handler de ProcesarFunction: descarga evidencia, extrae movimientos, responde.

Se invoca de forma asíncrona desde el webhook con el MensajeEntrante serializado.
"""

import os

from visible.adapters.outbound.dynamo_idempotencia import DynamoIdempotencia
from visible.adapters.outbound.dynamo_movimientos import DynamoRepositorioMovimientos
from visible.adapters.outbound.extractor_fake import FakeExtractor
from visible.adapters.outbound.media import MetaMediaDownloader
from visible.adapters.outbound.s3_evidencias import S3Evidencias
from visible.adapters.outbound.whatsapp_sender import WhatsAppSender
from visible.application.extractor import Contenido, Extractor
from visible.application.procesar import procesar
from visible.domain.mensaje import MensajeEntrante, desde_dict


def _crear_extractor() -> Extractor:
    if os.environ.get("EXTRACTOR", "fake") == "bedrock":
        from visible.adapters.outbound.extractor_bedrock import BedrockExtractor

        return BedrockExtractor()
    return FakeExtractor()


def _construir_contenido(mensaje: MensajeEntrante) -> Contenido:
    if mensaje.medios:
        media_id, mime = mensaje.medios[0]
        datos, mime_real = MetaMediaDownloader().descargar(media_id)
        mime_final = mime_real or mime
        S3Evidencias().guardar(mensaje.telefono, media_id, datos, mime_final)
        return Contenido(imagen=datos, mime_type=mime_final)
    return Contenido(texto=mensaje.texto)


def handler(event: dict, context: object) -> dict:
    mensaje = desde_dict(event)

    # Idempotencia: Meta reintenta; procesamos cada mensaje una sola vez.
    idempotencia = DynamoIdempotencia()
    if not idempotencia.reservar(mensaje.mensaje_id):
        return {"estado": "duplicado", "mensaje_id": mensaje.mensaje_id}

    try:
        contenido = _construir_contenido(mensaje)
        movimientos = procesar(
            mensaje.telefono,
            contenido,
            _crear_extractor(),
            DynamoRepositorioMovimientos(),
            WhatsAppSender(),
        )
    except Exception:
        # Libera la reserva para que el reintento async pueda reprocesar.
        idempotencia.liberar(mensaje.mensaje_id)
        raise
    return {"estado": "ok", "movimientos": len(movimientos)}
