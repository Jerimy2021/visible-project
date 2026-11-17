"""Respuestas del bot (texto peruano, cálido, máx 4 líneas). Puro y testeable.

Los datos llegan ya resueltos desde los adaptadores (nunca se inventan).
"""

TEXTO_NO_REGISTRADO = "No estás registrado 🙏 Habla con tu supervisor para que te dé acceso."
TEXTO_NO_ENTENDI = (
    "No te entendí 😅 Puedes preguntarme: ¿cuántos me faltan?, ¿dónde está HUA-00012?, "
    "mis P abiertos, o escribe «ya terminé»."
)

BOTONES = [
    ("bot|faltan", "Cuántos me faltan"),
    ("bot|p", "Mis P abiertos"),
    ("bot|fin", "Ya terminé"),
]
BOTONES_ADMIN = [
    ("adm|resumen", "Resumen"),
    ("adm|equipo", "Equipo"),
    ("adm|alertas", "Alertas"),
]


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


def texto_p_abiertos(abiertos: list[dict]) -> str:
    if not abiertos:
        return "No tienes P abiertos ✅ ¡Todo levantado!"
    lineas = [f"Tienes {len(abiertos)} P abiertos:"]
    for a in abiertos[:3]:
        puntos = ", ".join(a.get("puntos_p", [])) or "—"
        lineas.append(f"• {a['codigo']}: {puntos}")
    return "\n".join(lineas)


def texto_resumen(centro: dict) -> str:
    return (
        f"Avance del mes: {centro['avance_pct']}% ({centro['inspeccionados']}/{centro['total']}).\n"
        f"Te faltan {centro['faltan']}. P abiertos: {centro['p_abiertos']}."
    )


def texto_resumen_admin(centro: dict) -> str:
    ap = (
        centro["aprobacion"].get("estado")
        or f"{centro['aprobacion'].get('aprobadas')}/{centro['aprobacion'].get('plantas')}"
    )
    return (
        f"Centro de control · {centro['site']} {centro['periodo']}\n"
        f"Avance {centro['avance_pct']}% ({centro['inspeccionados']}/{centro['total']}) · faltan {centro['faltan']}\n"
        f"P abiertos {centro['p_abiertos']} · conformes 1ª {centro['conformes_1a_pct'] if centro['conformes_1a_pct'] is not None else '—'}%\n"
        f"Aprobación: {ap}"
    )


def texto_equipo(por_inspector: list[dict]) -> str:
    if not por_inspector:
        return "Aún no hay inspecciones registradas este mes."
    lineas = ["Avance por inspector:"]
    for i in por_inspector[:3]:
        lineas.append(f"• {i['inspector']}: {i['hechos']}/{i['asignados']}")
    return "\n".join(lineas)


def texto_alertas(abiertos: list[dict], atrasados: int) -> str:
    lineas = [f"Planta: {len(abiertos)} P abiertos · {atrasados} atrasados."]
    for a in abiertos[:3]:
        puntos = ", ".join(a.get("puntos_p", [])) or "—"
        lineas.append(f"• {a['codigo']}: {puntos}")
    return "\n".join(lineas)


def texto_felicitacion(nombre: str, marcados: int) -> str:
    quien = nombre.split(" ")[0] if nombre else "crack"
    if marcados == 0:
        return f"¡Gracias, {quien}! 🎉 Ya tenías todo reportado. Buen trabajo 🧯"
    return (
        f"¡Grande, {quien}! 🎉 Marqué tus {marcados} pendientes como reportados. "
        "Gracias por cuidar la planta 🧯"
    )
