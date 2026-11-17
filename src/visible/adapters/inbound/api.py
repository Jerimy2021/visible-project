"""API de solo lectura del Centro de control (HttpApi). Requiere header x-api-key.

GET /centro?site&periodo
GET /extintores?site&estado
GET /extintor/{codigo}
GET /inspectores/{id}/pendientes
"""

import hmac
import json
import os
from decimal import Decimal

from visible.adapters.outbound import repositorio_lectura as repo
from visible.adapters.outbound import secrets
from visible.domain.centro import centro
from visible.domain.extintores import en_alcance, estado_inspeccion
from visible.domain.fechas import hoy_lima
from visible.domain.usuarios import resolver_id

CORS = os.environ.get("CORS_ORIGIN", "*")


def _json(estado: int, cuerpo) -> dict:
    return {
        "statusCode": estado,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": CORS,
            "Access-Control-Allow-Methods": "GET,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,x-api-key",
        },
        "body": json.dumps(cuerpo, ensure_ascii=False, default=_serializar),
    }


def _serializar(x):
    if isinstance(x, Decimal):
        return int(x) if x == x.to_integral_value() else float(x)
    raise TypeError(type(x))


def _autorizado(event: dict) -> bool:
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    esperado = secrets.leer(os.environ["API_KEY_PARAM"], descifrar=True)
    return hmac.compare_digest(headers.get("x-api-key", ""), esperado)


def _periodo_actual() -> str:
    return hoy_lima().strftime("%Y-%m")


def handler(event: dict, context: object) -> dict:
    http = event.get("requestContext", {}).get("http", {})
    if http.get("method") == "OPTIONS":
        return _json(200, {})
    if not _autorizado(event):
        return _json(401, {"error": "api key inválida"})

    ruta = event.get("rawPath", "")
    qs = event.get("queryStringParameters") or {}
    pp = event.get("pathParameters") or {}

    if ruta == "/centro":
        site = qs.get("site", "Todas")
        periodo = qs.get("periodo") or _periodo_actual()
        return _json(200, centro(site, periodo, repo.cargar_datos()))

    if ruta == "/extintores":
        return _json(200, {"extintores": _listar_extintores(qs)})

    if pp.get("codigo"):
        return _ficha_extintor(pp["codigo"])

    if pp.get("id"):
        return _json(200, {"pendientes": _pendientes_inspector(pp["id"])})

    return _json(404, {"error": "ruta no encontrada"})


def _listar_extintores(qs: dict) -> list[dict]:
    site = qs.get("site", "Todas")
    filtro_estado = qs.get("estado", "")
    periodo = _periodo_actual()
    hoy = hoy_lima()
    exts = repo.scan_todo("TABLA_EXTINTORES")
    mants = repo.scan_todo("TABLA_MANTENIMIENTOS")
    por_cod: dict[str, list] = {}
    for m in mants:
        por_cod.setdefault(m["codigo"], []).append(m)

    filas = []
    for e in exts:
        if not en_alcance(e, site):
            continue
        estado = estado_inspeccion(e, por_cod.get(e["codigo"], []), periodo, hoy)
        if filtro_estado and estado != filtro_estado:
            continue
        filas.append(
            {
                "codigo": e["codigo"],
                "site": e.get("site"),
                "piso": e.get("piso"),
                "ubicacion": e.get("ubicacion"),
                "zona_brigada": e.get("zona_brigada"),
                "inspector_asignado": e.get("inspector_asignado"),
                "estado_inspeccion": estado,
            }
        )
    return sorted(filas, key=lambda x: x["codigo"])


def _ficha_extintor(codigo: str) -> dict:
    extintor = repo.obtener_extintor(codigo)
    if not extintor:
        return _json(404, {"error": "extintor no encontrado"})
    historial = sorted(
        repo.historial_extintor(codigo), key=lambda m: m.get("periodo", ""), reverse=True
    )
    return _json(200, {"extintor": extintor, "historial": historial})


def _pendientes_inspector(id_usuario: str) -> list[dict]:
    periodo = _periodo_actual()
    hoy = hoy_lima()
    usuarios = repo.scan_todo("TABLA_USUARIOS")
    exts = repo.scan_todo("TABLA_EXTINTORES")
    mants = repo.scan_todo("TABLA_MANTENIMIENTOS")
    por_cod: dict[str, list] = {}
    for m in mants:
        por_cod.setdefault(m["codigo"], []).append(m)

    pendientes = []
    for e in exts:
        if not e.get("activo"):
            continue
        if resolver_id(e.get("inspector_asignado", ""), usuarios) != id_usuario:
            continue
        estado = estado_inspeccion(e, por_cod.get(e["codigo"], []), periodo, hoy)
        if estado in ("POR HACER", "ATRASADO"):
            pendientes.append(
                {
                    "codigo": e["codigo"],
                    "ubicacion": e.get("ubicacion"),
                    "zona_brigada": e.get("zona_brigada"),
                    "estado_inspeccion": estado,
                }
            )
    return sorted(pendientes, key=lambda x: x["codigo"])
