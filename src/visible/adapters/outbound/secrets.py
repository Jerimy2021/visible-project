"""Lectura de parámetros desde SSM Parameter Store, cacheada a nivel de módulo."""

import os

_cache: dict[tuple[str, bool], str] = {}


def leer(nombre: str, *, descifrar: bool = False) -> str:
    """Lee un parámetro de SSM. descifrar=True para SecureString. Cachea el valor."""
    clave = (nombre, descifrar)
    if clave in _cache:
        return _cache[clave]

    import boto3  # import perezoso: el dominio/tests no requieren el SDK

    ssm = boto3.client("ssm")
    valor = ssm.get_parameter(Name=nombre, WithDecryption=descifrar)["Parameter"]["Value"]
    _cache[clave] = valor
    return valor


def invalidar(nombre: str, *, descifrar: bool = False) -> None:
    """Descarta el valor cacheado (p. ej. tras un 401 por token rotado)."""
    _cache.pop((nombre, descifrar), None)


def nombre_param(env_var: str) -> str:
    """Nombre del parámetro SSM configurado en una variable de entorno."""
    return os.environ[env_var]
