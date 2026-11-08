"""Puerto de salida: enviar mensajes al usuario (independiente del canal)."""

from typing import Protocol


class Mensajero(Protocol):
    """Puerto que implementan los adaptadores de salida (WhatsApp, etc.)."""

    def enviar_texto(self, telefono: str, texto: str) -> None: ...
