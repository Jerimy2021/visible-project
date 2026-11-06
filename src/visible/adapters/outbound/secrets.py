"""Lectura de secretos desde SSM Parameter Store (SecureString), cacheada."""

import os

_cache: dict[str, str] = {}


def obtener_token(param_name: str | None = None) -> str:
    """Lee el token de Twilio desde SSM con descifrado. Cachea a nivel de módulo."""
    nombre = param_name or os.environ["TWILIO_TOKEN_PARAM"]
    if nombre in _cache:
        return _cache[nombre]

    import boto3  # import perezoso: el dominio/tests no requieren el SDK

    ssm = boto3.client("ssm")
    resp = ssm.get_parameter(Name=nombre, WithDecryption=True)
    valor = resp["Parameter"]["Value"]
    _cache[nombre] = valor
    return valor
