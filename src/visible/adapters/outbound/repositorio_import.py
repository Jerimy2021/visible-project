"""Upsert idempotente a DynamoDB con reporte (nuevas / actualizadas / errores)."""


def upsert(
    tabla_nombre: str,
    items: list[dict],
    claves: list[str] | None = None,
    preservar_true: list[str] | None = None,
) -> dict:
    """Put de cada item (overwrite). Distingue nuevas de actualizadas con ALL_OLD.

    `preservar_true`: campos booleanos que nunca deben pasar de true a false (p. ej.
    `incumplio`): si el item previo lo tenía true y el nuevo no, se restaura con un update.
    """
    import boto3
    from botocore.exceptions import ClientError

    tabla = boto3.resource("dynamodb").Table(tabla_nombre)
    nuevas = 0
    actualizadas = 0
    errores: list[str] = []
    for item in items:
        try:
            resp = tabla.put_item(Item=item, ReturnValues="ALL_OLD")
            viejo = resp.get("Attributes")
            if viejo:
                actualizadas += 1
                _restaurar_true(tabla, item, viejo, claves, preservar_true)
            else:
                nuevas += 1
        except ClientError as e:
            errores.append(f"{item.get('codigo') or item.get('site') or '?'}: {e}")
    return {"nuevas": nuevas, "actualizadas": actualizadas, "errores": errores}


def _restaurar_true(tabla, item, viejo, claves, preservar_true) -> None:
    if not (preservar_true and claves):
        return
    faltan = [c for c in preservar_true if viejo.get(c) and not item.get(c)]
    if faltan:
        tabla.update_item(
            Key={k: item[k] for k in claves},
            UpdateExpression="SET " + ", ".join(f"{c} = :v{i}" for i, c in enumerate(faltan)),
            ExpressionAttributeValues={f":v{i}": True for i in range(len(faltan))},
        )
