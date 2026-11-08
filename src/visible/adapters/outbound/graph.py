"""Utilidad para peticiones a la Graph API con reintento ante token rotado."""

import urllib.error
from collections.abc import Callable

from visible.adapters.outbound import secrets


def ejecutar[T](token_param: str, fn: Callable[[str], T]) -> T:
    """Llama fn(token) leyendo el token de SSM. Si Graph responde 401, limpia el
    caché, relee el token de SSM y reintenta una sola vez."""
    for intento in range(2):
        token = secrets.leer(token_param, descifrar=True)
        try:
            return fn(token)
        except urllib.error.HTTPError as e:
            if e.code == 401 and intento == 0:
                secrets.invalidar(token_param, descifrar=True)
                continue
            raise
    raise RuntimeError("inalcanzable")
