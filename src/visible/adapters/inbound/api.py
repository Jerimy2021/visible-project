"""API de solo lectura para el panel del analista (HttpApi).

GET /perfiles                 -> lista con puntaje y estado.
GET /perfiles/{telefono}      -> ficha completa (indicadores, series, decisión,
                                 últimos 20 movimientos con URL prefirmada a la foto).
"""

import json
import os
from datetime import date
from decimal import Decimal

from visible.adapters.outbound.dynamo_movimientos import DynamoRepositorioMovimientos
from visible.adapters.outbound.dynamo_perfiles import DynamoPerfiles
from visible.domain.puntaje import ESTADO_APTA, ESTADO_FALTAN, ESTADO_PROCESO, evaluar

URL_TTL = 600  # 10 min
CORS = os.environ.get("CORS_ORIGIN", "*")
ORDEN_ESTADO = {ESTADO_APTA: 0, ESTADO_PROCESO: 1, ESTADO_FALTAN: 2}


def _json(estado: int, cuerpo) -> dict:
    return {
        "statusCode": estado,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": CORS,
            "Access-Control-Allow-Methods": "GET,OPTIONS",
        },
        "body": json.dumps(cuerpo, ensure_ascii=False, default=_serializar),
    }


def _serializar(x):
    if isinstance(x, Decimal):
        return float(x)
    raise TypeError(type(x))


def _presign(bucket: str, key: str) -> str | None:
    if not key:
        return None
    import boto3

    return boto3.client("s3").generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=URL_TTL
    )


def _resumen_perfil(perfil: dict, movs_repo: DynamoRepositorioMovimientos) -> dict:
    telefono = perfil["telefono"]
    ev = evaluar(movs_repo.leer_ventana(telefono, date.today()))
    return {
        "telefono": telefono,
        "nombre": perfil.get("nombre", ""),
        "rubro": perfil.get("rubro", ""),
        "zona": perfil.get("zona", ""),
        "puntaje": ev.puntaje,
        "estado": ev.estado,
        "ventas_semana_promedio": ev.ventas_semana_promedio,
    }


def _ficha(perfil: dict, movs_repo: DynamoRepositorioMovimientos, bucket: str) -> dict:
    telefono = perfil["telefono"]
    ev = evaluar(movs_repo.leer_ventana(telefono, date.today()))
    ultimos = []
    for it in movs_repo.ultimos(telefono, 20):
        ultimos.append(
            {
                "fecha": it.get("fecha"),
                "monto": it.get("monto"),
                "concepto": it.get("concepto", ""),
                "tipo": it.get("tipo"),
                "origen": it.get("origen", ""),
                "foto_url": _presign(bucket, it.get("evidencia_key", "")),
            }
        )
    return {
        "telefono": telefono,
        "nombre": perfil.get("nombre", ""),
        "rubro": perfil.get("rubro", ""),
        "zona": perfil.get("zona", ""),
        "consentimiento": perfil.get("consentimiento", ""),
        "evaluacion": ev.to_dict(),
        "movimientos": ultimos,
    }


def handler(event: dict, context: object) -> dict:
    ctx = event.get("requestContext", {}).get("http", {})
    if ctx.get("method") == "OPTIONS":
        return _json(200, {})

    perfiles_repo = DynamoPerfiles()
    movs_repo = DynamoRepositorioMovimientos()
    bucket = os.environ["BUCKET_EVIDENCIAS"]
    telefono = (event.get("pathParameters") or {}).get("telefono")

    if telefono:
        perfil = perfiles_repo.obtener(telefono)
        if not perfil:
            return _json(404, {"error": "perfil no encontrado"})
        return _json(200, _ficha(perfil, movs_repo, bucket))

    perfiles = [_resumen_perfil(p, movs_repo) for p in perfiles_repo.listar()]
    # Apta primero, luego En proceso, y Faltan datos al final; desempata por puntaje.
    perfiles.sort(key=lambda p: (ORDEN_ESTADO.get(p["estado"], 9), -p["puntaje"]))
    return _json(200, {"perfiles": perfiles})
