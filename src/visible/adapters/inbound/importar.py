"""Importador como servicio.

- `solicitar_url` (POST /import/url): devuelve una URL prefirmada para subir el CSV.
- `procesar_subida` (evento S3): al subir, hace upsert idempotente y escribe un
  reporte JSON (nuevas / actualizadas / errores) junto al archivo.
"""

import json
import logging
import os
from datetime import UTC, datetime

from visible.adapters.outbound.repositorio_import import upsert
from visible.domain.importacion import TABLAS, parsear, tabla_de_archivo

logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger("brigada.importar")

CORS = os.environ.get("CORS_ORIGIN", "*")
PREFIJO = "uploads/"


def _json(estado: int, cuerpo: dict) -> dict:
    return {
        "statusCode": estado,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": CORS,
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
        "body": json.dumps(cuerpo, ensure_ascii=False),
    }


def solicitar_url(event: dict, context: object) -> dict:
    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return _json(200, {})
    cuerpo = json.loads(event.get("body") or "{}")
    archivo = (cuerpo.get("archivo") or "").strip()
    if not tabla_de_archivo(archivo):
        return _json(400, {"error": f"archivo no reconocido: {archivo!r}"})

    import boto3

    key = f"{PREFIJO}{archivo}"
    url = boto3.client("s3").generate_presigned_url(
        "put_object",
        Params={"Bucket": os.environ["BUCKET_IMPORT"], "Key": key, "ContentType": "text/csv"},
        ExpiresIn=600,
    )
    return _json(200, {"url": url, "key": key, "metodo": "PUT"})


def importar_contenido(logico: str, contenido: bytes) -> dict:
    """Parsea y hace upsert de un CSV ya leído. Devuelve el reporte."""
    items, errores = parsear(logico, contenido)
    tabla_env = TABLAS[logico][1]
    resultado = (
        upsert(os.environ[tabla_env], items)
        if items
        else {"nuevas": 0, "actualizadas": 0, "errores": []}
    )
    return {
        "tabla": logico,
        "filas_validas": len(items),
        "nuevas": resultado["nuevas"],
        "actualizadas": resultado["actualizadas"],
        "errores": errores + resultado["errores"],
        "cuando": datetime.now(UTC).isoformat(),
    }


def procesar_subida(event: dict, context: object) -> dict:
    import boto3

    s3 = boto3.client("s3")
    reportes = []
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        if not key.startswith(PREFIJO):
            continue
        logico = tabla_de_archivo(key)
        if not logico:
            logger.warning("archivo no reconocido: %s", key)
            continue
        contenido = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        reporte = importar_contenido(logico, contenido)
        logger.info("import %s", json.dumps(reporte, ensure_ascii=False))
        s3.put_object(
            Bucket=bucket,
            Key=f"reports/{key.removeprefix(PREFIJO)}.json",
            Body=json.dumps(reporte, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )
        reportes.append(reporte)
    return {"reportes": reportes}
