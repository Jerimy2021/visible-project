"""Motor de puntaje crediticio (Python puro, sin AWS).

A partir de los movimientos de las últimas 4 semanas calcula indicadores,
un puntaje 0-100 explicable y una decisión de crédito sugerida.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from visible.domain.movimiento import Movimiento

# --- Parámetros (explícitos y explicables) ---------------------------------

DIAS_VENTANA = 28
SEMANAS = 4
PESOS = {"constancia": 30, "estabilidad": 25, "tendencia": 15, "margen": 20, "yape": 10}

UMBRAL_APTA = 70
UMBRAL_PROCESO = 50
MIN_SEMANAS = 3  # con <3 semanas de registro no se puede evaluar -> "Faltan datos"

# Crédito
TEA = Decimal("0.45")
PLAZO_MESES = 6
MONTOS = [500, 800, 1200, 2000, 3000]
CUOTA_MAX_RATIO = Decimal("0.10")  # cuota <= 10% de la base mensual

MARGEN_OBJETIVO = Decimal("0.45")

ESTADO_APTA = "Apta"
ESTADO_PROCESO = "En proceso"
ESTADO_FALTAN = "Faltan datos"


def _dec(x: float | Decimal) -> Decimal:
    return Decimal(str(x))


def _q2(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class Decision:
    monto: int
    cuota: Decimal
    plazo_meses: int
    tea: float
    ratio_cuota_excedente: float | None

    def to_dict(self) -> dict:
        return {
            "monto": self.monto,
            "cuota": float(self.cuota),
            "plazo_meses": self.plazo_meses,
            "tea": self.tea,
            "ratio_cuota_excedente": self.ratio_cuota_excedente,
        }


@dataclass
class Evaluacion:
    estado: str
    puntaje: int
    semanas_con_datos: int
    ventas_semana_promedio: float
    tendencia_pct: float
    estabilidad: str
    coef_variacion_pct: float
    constancia: float
    coincidencia_yape_pct: float | None
    ventas_por_semana: list[float]
    gastos_por_semana: list[float]
    heatmap: list[list[float]]
    subpuntajes: dict[str, float]
    decision: Decision
    pesos: dict[str, int] = field(default_factory=lambda: dict(PESOS))

    def to_dict(self) -> dict:
        return {
            "estado": self.estado,
            "puntaje": self.puntaje,
            "semanas_con_datos": self.semanas_con_datos,
            "ventas_semana_promedio": self.ventas_semana_promedio,
            "tendencia_pct": self.tendencia_pct,
            "estabilidad": self.estabilidad,
            "coef_variacion_pct": self.coef_variacion_pct,
            "constancia": self.constancia,
            "coincidencia_yape_pct": self.coincidencia_yape_pct,
            "ventas_por_semana": self.ventas_por_semana,
            "gastos_por_semana": self.gastos_por_semana,
            "heatmap": self.heatmap,
            "subpuntajes": self.subpuntajes,
            "pesos": self.pesos,
            "decision": self.decision.to_dict(),
        }


# --- Cálculos internos -----------------------------------------------------


def _semana(mov: Movimiento, hoy: date) -> int | None:
    """Índice de semana 0..3 (0 = más antigua, 3 = más reciente) o None si fuera de ventana."""
    dias = (hoy - mov.fecha).days
    if dias < 0 or dias >= DIAS_VENTANA:
        return None
    return SEMANAS - 1 - (dias // 7)


def _clamp(x: Decimal, lo: Decimal = Decimal(0), hi: Decimal = Decimal(1)) -> Decimal:
    return max(lo, min(hi, x))


def _cuota_francesa(principal: int) -> Decimal:
    """Cuota mensual, sistema francés, a partir de la TEA efectiva anual."""
    i = (Decimal(1) + TEA) ** (Decimal(1) / Decimal(12)) - Decimal(1)
    p = Decimal(principal)
    factor = Decimal(1) - (Decimal(1) + i) ** Decimal(-PLAZO_MESES)
    return _q2(p * i / factor)


def decidir_credito(base_semanal: Decimal) -> Decision:
    """Monto sugerido: el mayor cuya cuota sea <= 10% de la base mensual."""
    base_mensual = base_semanal * 4
    tope = base_mensual * CUOTA_MAX_RATIO
    elegido = 0
    cuota_elegida = Decimal(0)
    for monto in MONTOS:
        cuota = _cuota_francesa(monto)
        if cuota <= tope:
            elegido, cuota_elegida = monto, cuota
    ratio = None
    if elegido and base_mensual > 0:
        ratio = round(float(cuota_elegida / base_mensual), 4)
    return Decision(
        monto=elegido,
        cuota=cuota_elegida if elegido else Decimal("0.00"),
        plazo_meses=PLAZO_MESES,
        tea=float(TEA),
        ratio_cuota_excedente=ratio,
    )


def _estabilidad(cv_pct: float) -> tuple[str, Decimal]:
    if cv_pct < 15:
        return "Alta", Decimal("1.0")
    if cv_pct < 30:
        return "Media", Decimal("0.65")
    return "Baja", Decimal("0.3")


def evaluar(movimientos: list[Movimiento], hoy: date | None = None) -> Evaluacion:
    hoy = hoy or date.today()
    en_ventana = [(m, s) for m in movimientos if (s := _semana(m, hoy)) is not None]

    ventas_sem = [Decimal(0)] * SEMANAS
    gastos_sem = [Decimal(0)] * SEMANAS
    heatmap = [[Decimal(0)] * 7 for _ in range(SEMANAS)]
    dias_con_registro: set[date] = set()
    buckets_con_datos: set[int] = set()
    ventas: list[Movimiento] = []

    for m, s in en_ventana:
        buckets_con_datos.add(s)
        dias_con_registro.add(m.fecha)
        if m.es_venta:
            ventas_sem[s] += m.monto
            heatmap[s][m.fecha.weekday()] += m.monto
            ventas.append(m)
        else:
            gastos_sem[s] += m.monto

    semanas_con_datos = len(buckets_con_datos)
    presentes = sorted(buckets_con_datos)

    # Promedio semanal de ventas (sobre semanas con datos)
    prom_ventas = (
        sum((ventas_sem[s] for s in presentes), Decimal(0)) / semanas_con_datos
        if semanas_con_datos
        else Decimal(0)
    )

    # Tendencia %: primera vs última semana con datos
    tendencia = Decimal(0)
    if len(presentes) >= 2 and ventas_sem[presentes[0]] > 0:
        prim, ult = ventas_sem[presentes[0]], ventas_sem[presentes[-1]]
        tendencia = (ult - prim) / prim * 100

    # Estabilidad: coef. de variación de ventas semanales (semanas con datos)
    serie = [float(ventas_sem[s]) for s in presentes]
    if len(serie) >= 2 and statistics.mean(serie) > 0:
        cv = statistics.pstdev(serie) / statistics.mean(serie) * 100
    else:
        cv = 100.0
    etiqueta_estab, s_estab = _estabilidad(cv)

    constancia = len(dias_con_registro) / DIAS_VENTANA

    # Coincidencia Yape
    coincidencia: float | None = None
    if ventas and any(v.origen for v in ventas):
        yape = sum(1 for v in ventas if v.origen == "yape")
        coincidencia = round(100 * yape / len(ventas), 1)

    # Margen
    tot_v = sum((ventas_sem[s] for s in range(SEMANAS)), Decimal(0))
    tot_g = sum((gastos_sem[s] for s in range(SEMANAS)), Decimal(0))
    margen = (tot_v - tot_g) / tot_v if tot_v > 0 else Decimal(0)

    # Subpuntajes 0..1
    s_const = _clamp(_dec(constancia))
    s_tend = _clamp((_dec(tendencia) + 15) / 30)
    s_margen = _clamp(margen / MARGEN_OBJETIVO)
    s_yape = _dec(coincidencia / 100) if coincidencia is not None else Decimal("0.5")
    subs = {
        "constancia": float(round(s_const, 3)),
        "estabilidad": float(round(s_estab, 3)),
        "tendencia": float(round(s_tend, 3)),
        "margen": float(round(s_margen, 3)),
        "yape": float(round(s_yape, 3)),
    }

    puntaje = int(
        (
            PESOS["constancia"] * s_const
            + PESOS["estabilidad"] * s_estab
            + PESOS["tendencia"] * s_tend
            + PESOS["margen"] * s_margen
            + PESOS["yape"] * s_yape
        ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )

    if semanas_con_datos < MIN_SEMANAS:
        estado = ESTADO_FALTAN
    elif puntaje >= UMBRAL_APTA:
        estado = ESTADO_APTA
    else:
        estado = ESTADO_PROCESO

    # Base para el crédito: ganancia promedio semanal
    base_semanal = (tot_v - tot_g) / semanas_con_datos if semanas_con_datos else Decimal(0)

    return Evaluacion(
        estado=estado,
        puntaje=puntaje,
        semanas_con_datos=semanas_con_datos,
        ventas_semana_promedio=float(_q2(prom_ventas)),
        tendencia_pct=round(float(tendencia), 1),
        estabilidad=etiqueta_estab,
        coef_variacion_pct=round(cv, 1),
        constancia=round(constancia, 3),
        coincidencia_yape_pct=coincidencia,
        ventas_por_semana=[float(_q2(ventas_sem[s])) for s in range(SEMANAS)],
        gastos_por_semana=[float(_q2(gastos_sem[s])) for s in range(SEMANAS)],
        heatmap=[[float(_q2(c)) for c in fila] for fila in heatmap],
        subpuntajes=subs,
        decision=decidir_credito(base_semanal),
    )
