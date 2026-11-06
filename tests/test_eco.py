"""Caso de uso de eco."""

from visible.application.eco import construir_eco
from visible.domain.mensaje import MensajeEntrante


def test_eco_con_texto():
    msg = MensajeEntrante(telefono="+51999", texto="Hola", medios=())
    assert construir_eco(msg) == "Recibí: Hola"


def test_eco_con_medios():
    msg = MensajeEntrante(
        telefono="+51999",
        texto="",
        medios=(("https://x/img.jpg", "image/jpeg"),),
    )
    salida = construir_eco(msg)
    assert "1 archivo" in salida


def test_eco_vacio():
    msg = MensajeEntrante(telefono="+51999", texto="", medios=())
    assert construir_eco(msg) == "Recibí tu mensaje."
