"""Invocación asíncrona (InvocationType=Event) de la función del bot."""

import json
import os


def invocar_bot(payload: dict) -> None:
    import boto3

    boto3.client("lambda").invoke(
        FunctionName=os.environ["BOT_FUNCTION_NAME"],
        InvocationType="Event",
        Payload=json.dumps(payload).encode("utf-8"),
    )
