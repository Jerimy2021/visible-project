"""Modelo de dominio del mensaje entrante (sin dependencias de AWS)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MensajeEntrante:
    """Un mensaje recibido por WhatsApp, normalizado.

    medios: tupla de (media_id, mime_type) por cada archivo adjunto.
    """

    telefono: str
    texto: str
    medios: tuple[tuple[str, str], ...] = ()
    mensaje_id: str = ""


def a_dict(mensaje: MensajeEntrante) -> dict:
    """Serializa a dict JSON-compatible (payload de invocación async)."""
    return {
        "telefono": mensaje.telefono,
        "texto": mensaje.texto,
        "medios": [list(m) for m in mensaje.medios],
        "mensaje_id": mensaje.mensaje_id,
    }


def desde_dict(datos: dict) -> MensajeEntrante:
    """Reconstruye un MensajeEntrante desde el payload de invocación."""
    return MensajeEntrante(
        telefono=datos.get("telefono", ""),
        texto=datos.get("texto", ""),
        medios=tuple(tuple(m) for m in datos.get("medios", [])),
        mensaje_id=datos.get("mensaje_id", ""),
    )
