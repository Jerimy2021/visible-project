"""KPIs del Centro de control (reglas 05 + fórmulas 03a). Puro y testeable.

`datos` = {extintores, mantenimientos, aprobaciones, sites, usuarios} tal como
salen de DynamoDB (listas de dicts).
"""

from datetime import date
from statistics import mean

from visible.domain.extintores import en_alcance
from visible.domain.fechas import hoy_lima
from visible.domain.usuarios import resolver_id

PUNTOS = [
    ("precinto", "Precinto"),
    ("pasador", "Pasador"),
    ("presion", "Presión"),
    ("tarjeta", "Tarjeta"),
    ("libre_acceso", "Libre acceso"),
    ("senaletica", "Señalética"),
    ("gabinete", "Gabinete"),
    ("cilindro", "Cilindro"),
    ("manguera", "Manguera"),
]


def _num(x) -> int:
    try:
        return int(x)
    except (TypeError, ValueError):
        return 0


def puntos_no_cumple(m: dict) -> list[str]:
    return [et for col, et in PUNTOS if m.get(col) in ("NO_CUMPLE", "P")]


def incumple_ahora(m: dict) -> bool:
    """No cumple y aún no se levanta (pendiente abierto)."""
    if m.get("fecha_levantamiento"):
        return False
    return (
        _num(m.get("cantidad_p")) > 0
        or m.get("resultado") == "Con pendientes"
        or bool(puntos_no_cumple(m))
    )


def incumplio(m: dict) -> bool:
    """Alguna vez no cumplió (incluye ya levantados). Usa el flag si viene del importador."""
    if "incumplio" in m:
        return bool(m["incumplio"])
    return bool(
        incumple_ahora(m)
        or m.get("fecha_levantamiento")
        or m.get("resultado") in ("Con pendientes", "Conforme (levantado)")
    )


def _dias(desde: str, hasta: str) -> int:
    return (date.fromisoformat(hasta) - date.fromisoformat(desde)).days


def periodos_recientes(periodo: str, n: int = 6) -> list[str]:
    a, m = int(periodo[:4]), int(periodo[5:7])
    base = a * 12 + (m - 1)
    return [f"{(base - k) // 12:04d}-{(base - k) % 12 + 1:02d}" for k in range(n - 1, -1, -1)]


def _nombre(id_: str, raw: str, usuarios: list[dict]) -> str:
    for u in usuarios:
        if u.get("id") == id_:
            return u.get("nombre", raw)
    return raw


def _clave_inspector(nombre: str, usuarios: list[dict]) -> str:
    return resolver_id(nombre, usuarios) or nombre


def centro(site: str, periodo: str, datos: dict, hoy: date | None = None) -> dict:
    hoy = hoy or hoy_lima()
    usuarios = datos.get("usuarios", [])
    exts = [e for e in datos["extintores"] if en_alcance(e, site)]
    mants = [m for m in datos["mantenimientos"] if site == "Todas" or m.get("site") == site]
    sites = (
        datos["sites"]
        if site == "Todas"
        else [s for s in datos["sites"] if s.get("codigo") == site]
    )
    aprob = datos.get("aprobaciones", [])

    total = len(exts)
    mant_per = [m for m in mants if m.get("periodo") == periodo]
    inspeccionados = len({m["codigo"] for m in mant_per})
    nm = len(mant_per)
    conformes = len([m for m in mant_per if m.get("resultado") == "Conforme"])
    abiertos = [m for m in mants if incumple_ahora(m)]
    levantados = [m for m in mants if m.get("fecha_levantamiento") and m.get("fecha_inspeccion")]

    return {
        "site": site,
        "periodo": periodo,
        "total": total,
        "inspeccionados": inspeccionados,
        "faltan": max(0, total - inspeccionados),
        "avance_pct": round(100 * inspeccionados / total) if total else 0,
        "p_abiertos": len(abiertos),
        "conformes_1a_pct": round(100 * conformes / nm) if nm else None,
        "tiempo_levantamiento_dias": (
            round(mean(_dias(m["fecha_inspeccion"], m["fecha_levantamiento"]) for m in levantados))
            if levantados
            else None
        ),
        "inspectores_activos": len(
            {_clave_inspector(m["inspector"], usuarios) for m in mant_per if m.get("inspector")}
        ),
        "aprobacion": _aprobacion(site, periodo, aprob, sites),
        "por_planta": _por_planta(periodo, exts, mant_per, aprob, sites),
        "por_inspector": _por_inspector(exts, mant_per, usuarios),
        "punto_que_mas_falla": _punto_que_mas_falla(mant_per),
        "tendencia": _tendencia(periodo, mants, total),
        "no_cumple_por_mes": _no_cumple_por_mes(periodo, mants),
        "reincidentes": _reincidentes(periodo, mants),
        "alertas": {
            "pendientes": _pendientes(abiertos, hoy),
            "reincidentes": _reincidentes(periodo, mants)[:5],
        },
    }


def _del_site_periodo(site: str, periodo: str, mants: list[dict]) -> list[dict]:
    return [
        m
        for m in mants
        if m.get("periodo") == periodo and (site == "Todas" or m.get("site") == site)
    ]


def observaciones(site: str, periodo: str, datos: dict) -> list[dict]:
    """Movimientos del periodo con alguna observación (notas, adicionales o general)."""
    filas = []
    for m in _del_site_periodo(site, periodo, datos["mantenimientos"]):
        if (
            m.get("notas_puntos")
            or m.get("adicionales")
            or m.get("obs_general")
            or m.get("observacion")
        ):
            filas.append(
                {
                    "codigo": m["codigo"],
                    "site": m.get("site"),
                    "inspector": m.get("inspector"),
                    "notas_puntos": m.get("notas_puntos", ""),
                    "adicionales": m.get("adicionales", ""),
                    "obs_general": m.get("obs_general", ""),
                    "observacion": m.get("observacion", ""),
                }
            )
    return sorted(filas, key=lambda x: x["codigo"])


def no_cumplieron(site: str, periodo: str, datos: dict) -> list[dict]:
    """Extintores que no cumplieron ese mes, con qué y si ya se levantó."""
    filas = []
    for m in _del_site_periodo(site, periodo, datos["mantenimientos"]):
        if not incumplio(m):
            continue
        filas.append(
            {
                "codigo": m["codigo"],
                "site": m.get("site"),
                "inspector": m.get("inspector"),
                "puntos": puntos_no_cumple(m)
                or (["(detalle en obs)"] if m.get("observacion") else []),
                "resultado": m.get("resultado"),
                "levantado": bool(m.get("fecha_levantamiento")),
                "fecha_levantamiento": m.get("fecha_levantamiento", ""),
            }
        )
    return sorted(filas, key=lambda x: x["codigo"])


def _aprobacion(site: str, periodo: str, aprob: list[dict], sites: list[dict]) -> dict:
    if site == "Todas":
        aprobadas = len(
            [a for a in aprob if a.get("periodo") == periodo and a.get("estado") == "Aprobado"]
        )
        return {"aprobadas": aprobadas, "plantas": len(sites)}
    a = next((a for a in aprob if a.get("periodo") == periodo and a.get("site") == site), None)
    return {"estado": a.get("estado") if a else "Pendiente"}


def _por_planta(periodo, exts, mant_per, aprob, sites) -> list[dict]:
    filas = []
    for s in sites:
        cod = s.get("codigo")
        e_site = [e for e in exts if e.get("site") == cod]
        m_site = [m for m in mant_per if m.get("site") == cod]
        tot = len(e_site)
        ins = len({m["codigo"] for m in m_site})
        con_p = len({m["codigo"] for m in m_site if incumplio(m)})
        a = next((x for x in aprob if x.get("periodo") == periodo and x.get("site") == cod), None)
        filas.append(
            {
                "site": cod,
                "nombre": s.get("nombre", cod),
                "total": tot,
                "inspeccionados": ins,
                "con_p": con_p,
                "avance_pct": round(100 * ins / tot) if tot else 0,
                "estado_aprobacion": a.get("estado") if a else "Pendiente",
            }
        )
    return filas


def _por_inspector(exts, mant_per, usuarios) -> list[dict]:
    datos: dict[str, dict] = {}

    def fila(clave, nombre):
        return datos.setdefault(
            clave, {"inspector": nombre, "hechos": 0, "con_p": 0, "asignados": 0}
        )

    for e in exts:
        nombre = e.get("inspector_asignado", "")
        if nombre:
            clave = _clave_inspector(nombre, usuarios)
            fila(clave, _nombre(clave, nombre, usuarios))["asignados"] += 1
    for m in mant_per:
        nombre = m.get("inspector", "")
        if nombre:
            clave = _clave_inspector(nombre, usuarios)
            f = fila(clave, _nombre(clave, nombre, usuarios))
            f["hechos"] += 1
            if m.get("resultado") != "Conforme":
                f["con_p"] += 1
    return sorted(datos.values(), key=lambda x: x["hechos"], reverse=True)


def _punto_que_mas_falla(mant_per) -> list[dict]:
    filas = [
        {"punto": etiqueta, "p": len([m for m in mant_per if m.get(col) in ("NO_CUMPLE", "P")])}
        for col, etiqueta in PUNTOS
    ]
    return sorted(filas, key=lambda x: x["p"], reverse=True)


def _tendencia(periodo, mants, total) -> list[dict]:
    series = []
    for per in periodos_recientes(periodo, 6):
        ins = len({m["codigo"] for m in mants if m.get("periodo") == per})
        series.append({"periodo": per, "avance_pct": round(100 * ins / total) if total else 0})
    return series


def _reincidentes(periodo, mants) -> list[dict]:
    recientes = set(periodos_recientes(periodo, 6))
    fallidos = [m for m in mants if m.get("periodo") in recientes and incumplio(m)]
    por_cod: dict[str, set] = {}
    for m in fallidos:
        por_cod.setdefault(m["codigo"], set()).add(m["periodo"])
    filas = [{"codigo": c, "meses": len(p)} for c, p in por_cod.items() if len(p) >= 2]
    return sorted(filas, key=lambda x: x["meses"], reverse=True)


def _no_cumple_por_mes(periodo, mants) -> list[dict]:
    series = []
    for per in periodos_recientes(periodo, 6):
        codigos = {m["codigo"] for m in mants if m.get("periodo") == per and incumplio(m)}
        series.append({"periodo": per, "no_cumple": len(codigos)})
    return series


def _pendientes(abiertos, hoy) -> list[dict]:
    ordenados = sorted(abiertos, key=lambda m: m.get("fecha_inspeccion") or "9999")
    filas = []
    for m in ordenados[:5]:
        fi = m.get("fecha_inspeccion") or ""
        puntos = puntos_no_cumple(m)
        filas.append(
            {
                "codigo": m["codigo"],
                "fecha_inspeccion": fi,
                "dias_abierto": (hoy - date.fromisoformat(fi)).days if fi else None,
                "puntos_p": puntos,
            }
        )
    return filas
