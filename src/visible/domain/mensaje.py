"""Modelo de dominio del mensaje entrante (sin dependencias de AWS)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MensajeEntrante:
    """Un mensaje recibido por WhatsApp, normalizado.

    medios: tupla de (url, content_type) por cada archivo adjunto.
    """

    telefono: str
    texto: str
    medios: tuple[tuple[str, str], ...] = ()
