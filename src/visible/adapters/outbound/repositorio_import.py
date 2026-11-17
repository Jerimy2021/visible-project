"""Upsert idempotente a DynamoDB con reporte (nuevas / actualizadas / errores)."""


def upsert(tabla_nombre: str, items: list[dict]) -> dict:
    """Put de cada item (overwrite). Distingue nuevas de actualizadas con ALL_OLD."""
    import boto3
    from botocore.exceptions import ClientError

    tabla = boto3.resource("dynamodb").Table(tabla_nombre)
    nuevas = 0
    actualizadas = 0
    errores: list[str] = []
    for item in items:
        try:
            resp = tabla.put_item(Item=item, ReturnValues="ALL_OLD")
            if resp.get("Attributes"):
                actualizadas += 1
            else:
                nuevas += 1
        except ClientError as e:
            errores.append(f"{item.get('codigo') or item.get('site') or '?'}: {e}")
    return {"nuevas": nuevas, "actualizadas": actualizadas, "errores": errores}
