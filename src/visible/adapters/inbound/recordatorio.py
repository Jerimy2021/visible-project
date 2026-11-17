"""Recordatorio diario 8:00 a.m. Lima: plantilla a inspectores con faltantes."""

import logging
import os

from visible.adapters.inbound.bot import _pendientes_de
from visible.adapters.outbound import repositorio_lectura as repo
from visible.adapters.outbound.whatsapp_sender import WhatsAppSender
from visible.domain.fechas import hoy_lima

logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger("brigada.recordatorio")


def handler(event: dict, context: object) -> dict:
    hoy = hoy_lima()
    periodo = hoy.strftime("%Y-%m")
    datos = repo.cargar_datos()
    exts = datos["extintores"]
    por_cod: dict[str, list] = {}
    for m in datos["mantenimientos"]:
        por_cod.setdefault(m["codigo"], []).append(m)

    plantilla = os.environ.get("PLANTILLA_RECORDATORIO", "hello_world")
    idioma = os.environ.get("PLANTILLA_IDIOMA", "en_US")
    sender = WhatsAppSender()
    enviados = 0
    for u in datos["usuarios"]:
        if not (u.get("activo") and u.get("telefono_whatsapp") and u.get("rol") == "Inspector"):
            continue
        if _pendientes_de(u, exts, por_cod, periodo, hoy):
            sender.enviar_plantilla(u["telefono_whatsapp"], plantilla, idioma)
            enviados += 1
    logger.info("recordatorio enviados=%s", enviados)
    return {"enviados": enviados}
