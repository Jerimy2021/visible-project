"""Lectura de las tablas de Brigada desde DynamoDB."""

import os


def _tabla(nombre_env: str):
    import boto3

    return boto3.resource("dynamodb").Table(os.environ[nombre_env])


def scan_todo(nombre_env: str) -> list[dict]:
    tabla = _tabla(nombre_env)
    items: list[dict] = []
    kwargs: dict = {}
    while True:
        resp = tabla.scan(**kwargs)
        items += resp.get("Items", [])
        lek = resp.get("LastEvaluatedKey")
        if not lek:
            return items
        kwargs["ExclusiveStartKey"] = lek


def cargar_datos() -> dict:
    """Todas las listas para el Centro de control."""
    return {
        "sites": scan_todo("TABLA_SITES"),
        "extintores": scan_todo("TABLA_EXTINTORES"),
        "mantenimientos": scan_todo("TABLA_MANTENIMIENTOS"),
        "aprobaciones": scan_todo("TABLA_APROBACIONES"),
        "usuarios": scan_todo("TABLA_USUARIOS"),
    }


def obtener_extintor(codigo: str) -> dict | None:
    return _tabla("TABLA_EXTINTORES").get_item(Key={"codigo": codigo}).get("Item")


def historial_extintor(codigo: str) -> list[dict]:
    from boto3.dynamodb.conditions import Key

    resp = _tabla("TABLA_MANTENIMIENTOS").query(KeyConditionExpression=Key("codigo").eq(codigo))
    return resp.get("Items", [])
