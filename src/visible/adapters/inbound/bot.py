"""Handler del bot de WhatsApp (invocado async por el webhook).

Identifica al inspector por su teléfono, entiende la intención (botón o Bedrock
Haiku) y responde con datos del dominio. Nunca inventa cifras.
"""

import logging
from datetime import UTC, datetime

from visible.adapters.outbound import repositorio_lectura as repo
from visible.adapters.outbound.dynamo_idempotencia import DynamoIdempotencia
from visible.adapters.outbound.whatsapp_sender import WhatsAppSender
from visible.application import bot as texto
from visible.domain.centro import PUNTOS, centro
from visible.domain.extintores import ATRASADO, en_alcance, estado_inspeccion
from visible.domain.fechas import hoy_lima
from visible.domain.usuarios import resolver_id

logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger("brigada.bot")

_BOTON_A_INTENCION = {
    "bot|faltan": "faltan",
    "bot|p": "p_abiertos",
    "bot|fin": "ya_termine",
    "adm|resumen": "resumen",
    "adm|equipo": "equipo",
    "adm|alertas": "alertas",
}


def _pendientes_de(usuario, exts, por_cod, periodo, hoy):
    pend = []
    for e in exts:
        if not en_alcance(e, "Todas"):
            continue
        if resolver_id(e.get("inspector_asignado", ""), [usuario]) != usuario["id"]:
            continue
        if estado_inspeccion(e, por_cod.get(e["codigo"], []), periodo, hoy) in (
            "POR HACER",
            "ATRASADO",
        ):
            pend.append(e)
    return sorted(pend, key=lambda e: e["codigo"])


def _p_abiertos_de(usuario, mants):
    salida = []
    for m in mants:
        abierto = int(m.get("cantidad_p") or 0) > 0 and not m.get("fecha_levantamiento")
        if abierto and resolver_id(m.get("inspector", ""), [usuario]) == usuario["id"]:
            salida.append(
                {"codigo": m["codigo"], "puntos_p": [et for col, et in PUNTOS if m.get(col) == "P"]}
            )
    return salida


def _intencion(event: dict) -> dict:
    boton = event.get("boton", "")
    if boton in _BOTON_A_INTENCION:
        return {"intencion": _BOTON_A_INTENCION[boton], "codigo": ""}
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

    intencion = _intencion(event)
    logger.info("bot telefono=%s rol=%s intencion=%s", telefono, usuario.get("rol"), intencion)
    es_admin = usuario.get("rol") == "Administrador"
    respuesta = _responder(intencion, usuario, es_admin)
    sender.enviar_opciones(telefono, respuesta, texto.BOTONES_ADMIN if es_admin else texto.BOTONES)
    return {"estado": "ok", "intencion": intencion["intencion"]}


def _agrupar(mants: list[dict]) -> dict[str, list]:
    por_cod: dict[str, list] = {}
    for m in mants:
        por_cod.setdefault(m["codigo"], []).append(m)
    return por_cod


def _atrasados(site: str, datos: dict, periodo: str, hoy) -> int:
    por_cod = _agrupar(datos["mantenimientos"])
    return sum(
        1
        for e in datos["extintores"]
        if en_alcance(e, site)
        and estado_inspeccion(e, por_cod.get(e["codigo"], []), periodo, hoy) == ATRASADO
    )


def _responder(intencion: dict, usuario: dict, es_admin: bool) -> str:
    hoy = hoy_lima()
    periodo = hoy.strftime("%Y-%m")
    tipo = intencion["intencion"]

    if tipo == "donde":
        return texto.texto_donde(repo.obtener_extintor(intencion["codigo"]), intencion["codigo"])

    datos = repo.cargar_datos()
    c = centro("HUA", periodo, datos, hoy)

    if es_admin:
        if tipo == "equipo":
            return texto.texto_equipo(c["por_inspector"])
        if tipo == "alertas":
            return texto.texto_alertas(
                c["alertas"]["pendientes"], _atrasados("HUA", datos, periodo, hoy)
            )
        if tipo == "resumen":
            return texto.texto_resumen_admin(c)
        return texto.TEXTO_NO_ENTENDI

    if tipo == "resumen":
        return texto.texto_resumen(c)
    exts, mants = datos["extintores"], datos["mantenimientos"]
    por_cod = _agrupar(mants)
    if tipo == "p_abiertos":
        return texto.texto_p_abiertos(_p_abiertos_de(usuario, mants))
    if tipo == "faltan":
        pend = _pendientes_de(usuario, exts, por_cod, periodo, hoy)
        return texto.texto_faltan(len(pend), pend)
    if tipo == "ya_termine":
        pend = _pendientes_de(usuario, exts, por_cod, periodo, hoy)
        repo.guardar_mantenimientos([_fila_reportada(e, periodo, usuario, hoy) for e in pend])
        return texto.texto_felicitacion(usuario.get("nombre", ""), len(pend))
    return texto.TEXTO_NO_ENTENDI


def _fila_reportada(extintor: dict, periodo: str, usuario: dict, hoy) -> dict:
    return {
        "codigo": extintor["codigo"],
        "periodo": periodo,
        "site": extintor.get("site", ""),
        "inspector": usuario.get("nombre", ""),
        "fecha_inspeccion": hoy.isoformat(),
        "resultado": "Reportado (WhatsApp)",
        "cantidad_p": 0,
        "tipo_ejecutor": "Reporte WhatsApp",
        "creado_en": datetime.now(UTC).isoformat(),
    }
