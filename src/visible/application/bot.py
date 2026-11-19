"""Respuestas del bot (español peruano, cálido, máx 4 líneas). Puro y testeable.

Llama a la persona por su nombre corto; nunca inventa cifras (vienen del dominio).
"""

import random

TEXTO_NO_REGISTRADO = "No estás registrado 🙏 Habla con tu supervisor para que te dé acceso."

# Menús completos (lista de WhatsApp) y botones rápidos (máx 3) por rol.
MENU_INSPECTOR = [
    ("bot|faltan", "Cuántos me faltan"),
    ("bot|donde", "Dónde está un extintor"),
    ("bot|p", "Mis no cumple"),
    ("bot|fin", "Ya terminé"),
]
MENU_ADMIN = [
    ("adm|resumen", "Resumen"),
    ("adm|equipo", "Equipo"),
    ("adm|alertas", "Alertas"),
    ("adm|nocumple", "No cumplieron"),
    ("adm|obs", "Observaciones"),
]
RAPIDOS_INSPECTOR = [
    ("menu|", "Menú"),
    ("bot|faltan", "Cuántos me faltan"),
    ("bot|fin", "Ya terminé"),
]
RAPIDOS_ADMIN = [("menu|", "Menú"), ("adm|nocumple", "No cumplieron"), ("adm|resumen", "Resumen")]


def nombre_corto(nombre: str) -> str:
    return (nombre or "").split(" ")[0] or "crack"


def menu(es_admin: bool) -> list[tuple[str, str]]:
    return MENU_ADMIN if es_admin else MENU_INSPECTOR


def rapidos(es_admin: bool) -> list[tuple[str, str]]:
    return RAPIDOS_ADMIN if es_admin else RAPIDOS_INSPECTOR


def texto_bienvenida(nombre: str, es_admin: bool) -> str:
    n = nombre_corto(nombre)
    saludo = random.choice(["¡Hola", "¡Qué tal", "¡Buenas"])
    cierre = random.choice(["¿Qué necesitas hoy?", "¿En qué te ayudo?", "¿Qué quieres ver?"])
    quien = "Soy tu asistente de Inspectores en Acción 🧯"
    extra = (
        "Te ayudo a ver el avance y las alertas de la planta."
        if es_admin
        else "Te ayudo a llevar al día tus extintores."
    )
    return f"{saludo}, {n}! 👋 {quien}\n{extra} {cierre}"


def texto_no_entendi() -> str:
    return "Uy, no te entendí bien 😅 ¿Me ayudas eligiendo una opción?"


def pedir_codigo() -> str:
    return "Claro 🙌 ¿De qué extintor? Mándame su código (ej. HUA-00012)."


# --- Inspector -------------------------------------------------------------


def texto_faltan(total_faltan: int, cercanos: list[dict]) -> str:
    if total_faltan == 0:
        return "¡Ya los tienes todos! 🎉 No te falta ningún extintor este mes."
    lineas = [f"Te faltan {total_faltan} extintores este mes 🧯", "Los más cercanos:"]
    for e in cercanos[:3]:
        lineas.append(f"• {e['codigo']} · Piso {e.get('piso', '?')} · {e.get('ubicacion', '')}")
    return "\n".join(lineas)


def texto_donde(extintor: dict | None, codigo: str) -> str:
    if not extintor:
        return f"No encontré {codigo} 🤔 ¿Revisas el código? (ej. HUA-00012)"
    return (
        f"{extintor['codigo']} está en:\n"
        f"Piso {extintor.get('piso', '?')} · {extintor.get('ubicacion', '')}\n"
        f"Zona: {extintor.get('zona_brigada', '')}"
    )


def texto_no_cumple(abiertos: list[dict]) -> str:
    if not abiertos:
        return "No tienes ningún «No cumple» abierto ✅ ¡Todo levantado!"
    lineas = [f"Tienes {len(abiertos)} «No cumple» por levantar:"]
    for a in abiertos[:3]:
        lineas.append(f"• {a['codigo']}: {', '.join(a.get('puntos_p', [])) or '—'}")
    return "\n".join(lineas)


def texto_felicitacion(nombre: str, marcados: int) -> str:
    n = nombre_corto(nombre)
    if marcados == 0:
        return f"¡Gracias, {n}! 🎉 Ya tenías todo reportado. Buen trabajo 💪"
    frase = random.choice(
        [
            f"¡Excelente trabajo, {n}! 🎉 Completaste tus extintores del mes.",
            f"¡Grande, {n}! 🎉 Terminaste tu ronda del mes.",
            f"¡Lo lograste, {n}! 🎉 Marqué tus {marcados} pendientes como listos.",
        ]
    )
    return f"{frase} Gracias por cuidar a todos 💪"


# --- Admin -----------------------------------------------------------------


def texto_resumen(centro: dict) -> str:
    return (
        f"Avance del mes: {centro['avance_pct']}% ({centro['inspeccionados']}/{centro['total']}).\n"
        f"Te faltan {centro['faltan']}. No cumple: {centro['p_abiertos']}."
    )


def texto_resumen_admin(centro: dict) -> str:
    ap = (
        centro["aprobacion"].get("estado")
        or f"{centro['aprobacion'].get('aprobadas')}/{centro['aprobacion'].get('plantas')}"
    )
    conf = centro["conformes_1a_pct"]
    ins = f"{centro['inspeccionados']}/{centro['total']}"
    return (
        f"Centro de control · {centro['site']} {centro['periodo']}\n"
        f"Avance {centro['avance_pct']}% ({ins}) · faltan {centro['faltan']}\n"
        f"No cumple abiertos {centro['p_abiertos']} · "
        f"conformes 1ª {conf if conf is not None else '—'}%\n"
        f"Aprobación: {ap}"
    )


def texto_equipo(por_inspector: list[dict]) -> str:
    if not por_inspector:
        return "Aún no hay inspecciones registradas este mes."
    lineas = ["Avance por inspector:"]
    for i in por_inspector[:4]:
        lineas.append(f"• {nombre_corto(i['inspector'])}: {i['hechos']}/{i['asignados']}")
    return "\n".join(lineas)


def texto_alertas(abiertos: list[dict], atrasados: int) -> str:
    lineas = [f"Planta: {len(abiertos)} «No cumple» abiertos · {atrasados} atrasados."]
    for a in abiertos[:3]:
        lineas.append(f"• {a['codigo']}: {', '.join(a.get('puntos_p', [])) or '—'}")
    return "\n".join(lineas)


def texto_no_cumplieron(site: str, periodo: str, filas: list[dict]) -> str:
    if not filas:
        return f"En {site} ({periodo}) todos cumplieron ✅"
    lineas = [f"No cumplieron en {site} ({periodo}): {len(filas)}"]
    for f in filas[:3]:
        marca = " ✓ levantado" if f.get("levantado") else ""
        lineas.append(f"• {f['codigo']}: {', '.join(f.get('puntos', [])) or '—'}{marca}")
    return "\n".join(lineas)


def texto_no_cumple_meses(serie: list[dict], site: str) -> str:
    lineas = [f"No cumplieron por mes en {site}:"]
    for s in serie:
        lineas.append(f"• {s['periodo']}: {s['no_cumple']}")
    return "\n".join(lineas)


def texto_observaciones(site: str, periodo: str, filas: list[dict]) -> str:
    if not filas:
        return f"Sin observaciones en {site} ({periodo})."
    lineas = [f"Observaciones en {site} ({periodo}): {len(filas)}"]
    for f in filas[:3]:
        obs = (
            f.get("obs_general")
            or f.get("adicionales")
            or f.get("notas_puntos")
            or f.get("observacion")
            or "—"
        )
        lineas.append(f"• {f['codigo']}: {obs[:70]}")
    return "\n".join(lineas)
