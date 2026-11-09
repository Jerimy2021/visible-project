"""Vista de la emprendedora: su semana, su ahorro y su camino al crédito.

Python puro (sin AWS). Usa las mismas categorías que el puntaje:
- Ganancia del negocio = ventas − gastos del negocio.
- Ahorro = ganancia − gastos personales − cuotas de deuda pagadas.
  (Un préstamo recibido NO es ingreso ni ahorro: no se suma ni se resta.)
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from decimal import Decimal

from visible.domain.movimiento import Categoria, Movimiento

_LETRAS = ["L", "M", "M", "J", "V", "S", "D"]


def id_opaco(telefono: str) -> str:
    """Id de la ruta del panel: nunca expone el teléfono."""
    return hashlib.sha256(f"visible:{telefono}".encode()).hexdigest()[:16]


def _f(x: Decimal) -> float:
    return float(x.quantize(Decimal("0.01")))


def _rango(movs: list[Movimiento], hoy: date, desde: int, hasta: int) -> list[Movimiento]:
    """Movimientos con desde <= días atrás < hasta (0 = hoy)."""
    return [m for m in movs if desde <= (hoy - m.fecha).days < hasta]


def _es_cuota(m: Movimiento) -> bool:
    return m.categoria is Categoria.DEUDA and m.subcategoria != "prestamo_recibido"


def totales(movs: list[Movimiento]) -> dict[str, float]:
    def suma(pred) -> Decimal:
        return sum((m.monto for m in movs if pred(m)), Decimal(0))

    ventas = suma(lambda m: m.categoria is Categoria.INGRESO)
    negocio = suma(lambda m: m.categoria is Categoria.GASTO_NEGOCIO)
    personal = suma(lambda m: m.categoria is Categoria.GASTO_PERSONAL)
    cuotas = suma(_es_cuota)
    ganancia = ventas - negocio
    return {
        "ventas": _f(ventas),
        "gastos_negocio": _f(negocio),
        "gastos_personales": _f(personal),
        "cuotas_deuda": _f(cuotas),
        "ganancia": _f(ganancia),
        "ahorro": _f(ganancia - personal - cuotas),
        "por_cobrar": _f(suma(lambda m: m.categoria is Categoria.INGRESO and m.por_cobrar)),
        "por_clasificar": _f(suma(lambda m: m.categoria is Categoria.POR_CLASIFICAR)),
    }


def _por_subcategoria(movs: list[Movimiento]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, Decimal]] = {}
    for m in movs:
        if m.categoria in (Categoria.MOVIMIENTO_INTERNO, Categoria.POR_CLASIFICAR):
            continue
        sub = m.subcategoria or "otros"
        cat = out.setdefault(m.categoria.value, {})
        cat[sub] = cat.get(sub, Decimal(0)) + m.monto
    return {c: {s: _f(v) for s, v in subs.items()} for c, subs in out.items()}


def resumen_emprendedora(movs: list[Movimiento], hoy: date) -> dict:
    """Datos para 'Mi negocio': últimos 7 días, últimas 4 semanas y camino al crédito."""
    semana = _rango(movs, hoy, 0, 7)
    anterior = _rango(movs, hoy, 7, 14)
    mes = _rango(movs, hoy, 0, 28)

    t_sem = totales(semana)
    t_ant = totales(anterior)
    variacion = None
    if t_ant["ganancia"]:
        variacion = round((t_sem["ganancia"] - t_ant["ganancia"]) / abs(t_ant["ganancia"]) * 100, 1)

    por_dia = []
    for atras in range(6, -1, -1):
        dia = hoy - timedelta(days=atras)
        t = totales([m for m in semana if m.fecha == dia])
        por_dia.append(
            {"fecha": dia.isoformat(), "letra": _LETRAS[dia.weekday()], "ganancia": t["ganancia"]}
        )

    dias_registro_7 = len(
        {m.fecha for m in semana if m.categoria is not Categoria.MOVIMIENTO_INTERNO}
    )
    return {
        "desde": (hoy - timedelta(days=6)).isoformat(),
        "hasta": hoy.isoformat(),
        "semana": t_sem,
        "variacion_ganancia_pct": variacion,
        "por_dia": por_dia,
        "mes": totales(mes),
        "subcategorias_mes": _por_subcategoria(mes),
        "dias_con_registro_7": dias_registro_7,
    }
