"""Caso de uso: construir la respuesta de eco a un mensaje entrante."""

from visible.domain.mensaje import MensajeEntrante


def construir_eco(mensaje: MensajeEntrante) -> str:
    """Devuelve el texto de respuesta (eco) para un mensaje entrante."""
    partes: list[str] = []
    if mensaje.texto:
        partes.append(f"Recibí: {mensaje.texto}")
    if mensaje.medios:
        partes.append(f"({len(mensaje.medios)} archivo(s) adjunto(s))")
    if not partes:
        return "Recibí tu mensaje."
    return " ".join(partes)
