"""Motor de puntaje: indicadores, estados y decisión de crédito."""

from datetime import date, timedelta
from decimal import Decimal

from visible.domain.movimiento import Movimiento, TipoMovimiento
from visible.domain.puntaje import (
    _cuota_francesa,
    decidir_credito,
    evaluar,
)

HOY = date(2026, 11, 8)


def venta(dias_atras: int, monto: str, origen: str = "") -> Movimiento:
    return Movimiento(
        HOY - timedelta(days=dias_atras), Decimal(monto), "venta", TipoMovimiento.VENTA, 0.9, origen
    )


def gasto(dias_atras: int, monto: str, tipo=TipoMovimiento.GASTO_NEGOCIO) -> Movimiento:
    return Movimiento(HOY - timedelta(days=dias_atras), Decimal(monto), "gasto", tipo, 0.9)


def test_cuota_francesa_conocida():
    # TEA 45% efectiva anual, 6 meses, P=500 -> ~S/ 92.6
    cuota = _cuota_francesa(500)
    assert Decimal("92") < cuota < Decimal("93")


def test_decision_elige_mayor_monto_bajo_tope():
    # base mensual 1600 -> tope cuota 160 -> cuota(800)=148 ok, cuota(1200)=222 no
    d = decidir_credito(Decimal("400"))
    assert d.monto == 800
    assert d.plazo_meses == 6
    assert d.tea == 0.45
    assert d.ratio_cuota_excedente is not None and d.ratio_cuota_excedente <= 0.10


def test_decision_sin_capacidad():
    d = decidir_credito(Decimal("50"))  # base mensual 200 -> tope 20 < cuota(500)
    assert d.monto == 0
    assert d.ratio_cuota_excedente is None


def test_faltan_datos_con_menos_de_3_semanas():
    movs = [venta(1, "100"), venta(2, "100"), venta(8, "100")]  # 2 semanas
    ev = evaluar(movs, hoy=HOY)
    assert ev.semanas_con_datos == 2
    assert ev.estado == "Faltan datos"
    assert ev.puntaje is None


def test_estabilidad_alta_y_constancia():
    # 4 semanas, ventas parejas (~igual) y registro 4 días/semana
    movs = []
    for sem in range(4):
        for d in range(4):
            movs.append(venta(sem * 7 + d, "100"))
    ev = evaluar(movs, hoy=HOY)
    assert ev.semanas_con_datos == 4
    assert ev.estabilidad == "Alta"
    assert ev.coef_variacion_pct < 15
    assert ev.constancia == round(16 / 28, 3)
    assert ev.ventas_semana_promedio == 400.0


def test_coincidencia_yape_null_sin_origen():
    ev = evaluar([venta(1, "100"), venta(2, "100")], hoy=HOY)
    assert ev.coincidencia_yape_pct is None


def test_coincidencia_yape_porcentaje():
    movs = [venta(1, "100", "yape"), venta(2, "100", "efectivo"), venta(3, "100", "yape")]
    ev = evaluar(movs, hoy=HOY)
    assert ev.coincidencia_yape_pct == round(100 * 2 / 3, 1)


def test_tendencia_positiva():
    # semana más antigua 100, más reciente 200 -> +100%
    movs = [venta(21, "100"), venta(0, "200")]
    ev = evaluar(movs, hoy=HOY)
    assert ev.tendencia_pct == 100.0
