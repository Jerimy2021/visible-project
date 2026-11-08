"""Dominio Movimiento + caso de uso `procesar` con dobles en memoria."""

from datetime import date
from decimal import Decimal

from visible.adapters.outbound.extractor_fake import FakeExtractor
from visible.application.extractor import Contenido
from visible.application.procesar import MENSAJE_SIN_DATOS, procesar, resumir
from visible.domain.movimiento import Movimiento, TipoMovimiento


class RepoMemoria:
    def __init__(self):
        self.guardados: list[tuple[str, list[Movimiento]]] = []

    def guardar(self, telefono, movimientos):
        self.guardados.append((telefono, movimientos))


class MensajeroMemoria:
    def __init__(self):
        self.enviados: list[tuple[str, str]] = []

    def enviar_texto(self, telefono, texto):
        self.enviados.append((telefono, texto))


class ExtractorVacio:
    def extraer(self, contenido):
        return []


def test_movimiento_es_venta():
    m = Movimiento(date.today(), Decimal("10"), "x", TipoMovimiento.VENTA, 0.9)
    g = Movimiento(date.today(), Decimal("10"), "x", TipoMovimiento.GASTO_CASA, 0.9)
    assert m.es_venta and not g.es_venta


def test_resumir_totales():
    hoy = date.today()
    movs = [
        Movimiento(hoy, Decimal("135.00"), "blusas", TipoMovimiento.VENTA, 0.9),
        Movimiento(hoy, Decimal("65.00"), "polos", TipoMovimiento.VENTA, 0.9),
        Movimiento(hoy, Decimal("120.00"), "tela", TipoMovimiento.GASTO_NEGOCIO, 0.8),
    ]
    assert resumir(movs) == "Registré 2 ventas por S/ 200.00 y 1 gastos por S/ 120.00. ¿Está bien?"


def test_procesar_guarda_y_confirma():
    repo, mensajero = RepoMemoria(), MensajeroMemoria()
    movs = procesar("51999", Contenido(texto="x"), FakeExtractor(), repo, mensajero)
    assert len(movs) == 5
    assert repo.guardados == [("51999", movs)]
    assert mensajero.enviados[0][0] == "51999"
    assert "Registré 3 ventas" in mensajero.enviados[0][1]


def test_procesar_sin_datos_no_guarda():
    repo, mensajero = RepoMemoria(), MensajeroMemoria()
    movs = procesar("51999", Contenido(texto="borroso"), ExtractorVacio(), repo, mensajero)
    assert movs == []
    assert repo.guardados == []
    assert mensajero.enviados == [("51999", MENSAJE_SIN_DATOS)]
