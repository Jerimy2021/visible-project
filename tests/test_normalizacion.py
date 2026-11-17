from decimal import Decimal

from visible.domain.fechas import normalizar_fecha
from visible.domain.normalizacion import booleano, nombre_canonico, numero, texto


def test_fecha():
    assert normalizar_fecha("01/01/2017 00:00") == "2017-01-01"
    assert normalizar_fecha("29/10/2026") == "2026-10-29"
    assert normalizar_fecha("") == ""
    assert normalizar_fecha("sin fecha") == ""


def test_booleano():
    assert booleano("Verdadero") is True
    assert booleano("Sí") is True
    assert booleano("No") is False
    assert booleano("") is None


def test_texto_na():
    assert texto(" N/A ") == "NA"
    assert texto("n/a") == "NA"
    assert texto("OK") == "OK"


def test_numero():
    assert numero("20") == Decimal("20")
    assert numero("") is None
    assert numero("x") is None


def test_nombre_canonico():
    assert nombre_canonico("  Miguel  Guzmán  ") == "miguel guzman"
    assert nombre_canonico("José Manuel") == "jose manuel"
