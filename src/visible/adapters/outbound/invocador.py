"""Invocación asíncrona (InvocationType=Event) de la función de procesamiento."""

import json
import os


def invocar_procesar(payload: dict) -> None:
    import boto3

    boto3.client("lambda").invoke(
        FunctionName=os.environ["PROCESAR_FUNCTION_NAME"],
        InvocationType="Event",
        Payload=json.dumps(payload).encode("utf-8"),
    )
