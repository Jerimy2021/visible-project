"""Handler del bot de WhatsApp (invocado async por el webhook).

Identifica al usuario por su teléfono, entiende la intención (botón o Bedrock) y
responde con datos del dominio. Admin ve todas las plantas; inspector solo la suya.
"""

import logging
from datetime import UTC, datetime

from visible.adapters.outbound import repositorio_lectura as repo
from visible.adapters.outbound.dynamo_idempotencia import DynamoIdempotencia
from visible.adapters.outbound.whatsapp_sender import WhatsAppSender
from visible.application import bot as texto
from visible.domain.centro import (
    PUNTOS,
    centro,
    incumple_ahora,
    no_cumplieron,
    observaciones,
    puntos_no_cumple,
)
from visible.domain.extintores import ATRASADO, en_alcance, estado_inspeccion
from visible.domain.fechas import hoy_lima
from visible.domain.usuarios import resolver_id

logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger("brigada.bot")

_BOTON = {
    "bot|faltan": "faltan",
    "bot|donde": "donde",
    "bot|p": "p_abiertos",
    "bot|fin": "ya_termine",
    "adm|resumen": "resumen",
    "adm|equipo": "equipo",
    "adm|alertas": "alertas",
    "adm|nocumple": "no_cumplieron",
    "adm|obs": "observaciones",
}
_MESES = {
    m: f"{i:02d}"
    for i, m in enumerate(
        [
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "setiembre",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ],
        start=1,
    )
}
_MESES["septiembre"] = "09"


def _mes_a_periodo(mes: str, actual: str) -> str:
    if not mes:
        return actual
    if len(mes) == 7 and mes[4] == "-":
        return mes
    num = _MESES.get(mes.lower())
    return f"{actual[:4]}-{num}" if num else actual


def _pendientes_de(usuario, exts, por_cod, periodo, hoy):
    pend = []
    for e in exts:
        if not en_alcance(e, "Todas"):
            continue
        if resolver_id(e.get("inspector_asignado", ""), [usuario]) != usuario["id"]:
            continue
        if estado_inspeccion(e, por_cod.get(e["codigo"], []), periodo, hoy) in (
            "POR HACER",
            ATRASADO,
        ):
            pend.append(e)
    return sorted(pend, key=lambda e: e["codigo"])


def _no_cumple_de(usuario, mants):
    salida = []
    for m in mants:
        if incumple_ahora(m) and resolver_id(m.get("inspector", ""), [usuario]) == usuario["id"]:
            salida.append({"codigo": m["codigo"], "puntos_p": puntos_no_cumple(m)})
    return salida


def _intencion(event: dict) -> dict:
    boton = event.get("boton", "")
    if boton == "menu|":
        return {"intencion": "menu", "codigo": "", "site": "", "mes": ""}
    if boton in _BOTON:
        return {"intencion": _BOTON[boton], "codigo": "", "site": "", "mes": ""}
    from visible.adapters.outbound.intenciones_bedrock import clasificar

    return clasificar(event.get("texto", ""))


def handler(event: dict, context: object) -> dict:
    telefono = event.get("telefono", "")
    sender = WhatsAppSender()
    if not DynamoIdempotencia().reservar(event.get("mensaje_id", "")):
        return {"estado": "duplicado"}

    usuario = repo.usuario_por_telefono(telefono)
    if not usuario:
        sender.enviar_texto(telefono, texto.TEXTO_NO_REGISTRADO)
        return {"estado": "no_registrado"}

    es_admin = usuario.get("rol") == "Administrador"
    intencion = _intencion(event)
    tipo = intencion["intencion"]
    logger.info("bot telefono=%s rol=%s intencion=%s", telefono, usuario.get("rol"), tipo)

    if tipo in ("menu", "saludo", "otro"):
        aviso = (
            texto.texto_no_entendi()
            if tipo == "otro"
            else texto.texto_bienvenida(usuario.get("nombre", ""), es_admin)
        )
        sender.enviar_opciones(telefono, aviso, texto.menu(es_admin))
        return {"estado": tipo}

    respuesta = _responder(intencion, usuario, es_admin)
    sender.enviar_opciones(telefono, respuesta, texto.rapidos(es_admin))
    return {"estado": "ok", "intencion": tipo}


def _agrupar(mants):
    por_cod: dict[str, list] = {}
    for m in mants:
        por_cod.setdefault(m["codigo"], []).append(m)
    return por_cod


def _atrasados(site, datos, periodo, hoy):
    por_cod = _agrupar(datos["mantenimientos"])
    return sum(
        1
        for e in datos["extintores"]
        if en_alcance(e, site)
        and estado_inspeccion(e, por_cod.get(e["codigo"], []), periodo, hoy) == ATRASADO
    )


def _site_inspector(usuario, datos) -> str:
    for e in datos["extintores"]:
        if resolver_id(e.get("inspector_asignado", ""), [usuario]) == usuario["id"]:
            return e.get("site", "HUA")
    return "HUA"


def _responder(intencion: dict, usuario: dict, es_admin: bool) -> str:
    hoy = hoy_lima()
    actual = hoy.strftime("%Y-%m")
    tipo = intencion["intencion"]

    if tipo == "donde":
        if not intencion.get("codigo"):
            return texto.pedir_codigo()
        return texto.texto_donde(repo.obtener_extintor(intencion["codigo"]), intencion["codigo"])

    datos = repo.cargar_datos()
    periodo = _mes_a_periodo(intencion.get("mes", ""), actual)

    if es_admin:
        site = intencion.get("site") or "Todas"
        if tipo == "equipo":
            return texto.texto_equipo(centro(site, periodo, datos, hoy)["por_inspector"])
        if tipo == "alertas":
            c = centro(site, periodo, datos, hoy)
            return texto.texto_alertas(
                c["alertas"]["pendientes"], _atrasados(site, datos, periodo, hoy)
            )
        if tipo == "no_cumplieron":
            return texto.texto_no_cumplieron(site, periodo, no_cumplieron(site, periodo, datos))
        if tipo == "no_cumplieron_meses":
            return texto.texto_no_cumple_meses(
                centro(site, periodo, datos, hoy)["no_cumple_por_mes"], site
            )
        if tipo == "observaciones":
            return texto.texto_observaciones(site, periodo, observaciones(site, periodo, datos))
        if tipo == "resumen":
            return texto.texto_resumen_admin(centro(site, periodo, datos, hoy))
        return texto.texto_no_entendi()

    # Inspector: siempre su planta.
    site = _site_inspector(usuario, datos)
    if tipo == "resumen":
        return texto.texto_resumen(centro(site, actual, datos, hoy))
    exts, mants = datos["extintores"], datos["mantenimientos"]
    por_cod = _agrupar(mants)
    if tipo == "p_abiertos":
        return texto.texto_no_cumple(_no_cumple_de(usuario, mants))
    if tipo == "faltan":
        pend = _pendientes_de(usuario, exts, por_cod, actual, hoy)
        return texto.texto_faltan(len(pend), pend)
    if tipo == "ya_termine":
        pend = _pendientes_de(usuario, exts, por_cod, actual, hoy)
        repo.guardar_mantenimientos([_fila_reportada(e, actual, usuario, hoy) for e in pend])
        return texto.texto_felicitacion(usuario.get("nombre", ""), len(pend))
    return texto.texto_no_entendi()


def _fila_reportada(extintor, periodo, usuario, hoy) -> dict:
    fila = {
        "codigo": extintor["codigo"],
        "periodo": periodo,
        "site": extintor.get("site", ""),
        "inspector": usuario.get("nombre", ""),
        "fecha_inspeccion": hoy.isoformat(),
        "resultado": "Reportado (WhatsApp)",
        "cantidad_p": 0,
        "incumplio": False,
        "tipo_ejecutor": "Reporte WhatsApp",
        "creado_en": datetime.now(UTC).isoformat(),
    }
    for col, _ in PUNTOS:
        fila[col] = "CUMPLE"
    return fila
