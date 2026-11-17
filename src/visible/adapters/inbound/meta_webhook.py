"""Webhook de Meta WhatsApp (verificación + firma) que invoca el bot async."""

import base64
import hashlib
import hmac
import json
import os

from visible.adapters.outbound import secrets
from visible.adapters.outbound.invocador import invocar_bot


def firmar(app_secret: str, raw: bytes) -> str:
    return "sha256=" + hmac.new(app_secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()


def firma_valida(app_secret: str, raw: bytes, cabecera: str) -> bool:
    return hmac.compare_digest(firmar(app_secret, raw), cabecera or "")


def responder_verificacion(mode: str, token: str, challenge: str, esperado: str) -> dict:
    if mode == "subscribe" and hmac.compare_digest(token or "", esperado):
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/plain"},
            "body": challenge or "",
        }
    return {"statusCode": 403, "headers": {"Content-Type": "text/plain"}, "body": "Forbidden"}


def _a_evento(msg: dict) -> dict:
    telefono = msg.get("from", "")
    mensaje_id = msg.get("id", "")
    if msg.get("type") == "interactive":
        inter = msg.get("interactive", {})
        reply = inter.get("button_reply") or inter.get("list_reply") or {}
        return {
            "telefono": telefono,
            "boton": reply.get("id", ""),
            "texto": "",
            "mensaje_id": mensaje_id,
        }
    texto = msg.get("text", {}).get("body", "") if msg.get("type") == "text" else ""
    return {"telefono": telefono, "boton": "", "texto": texto, "mensaje_id": mensaje_id}


def _mensajes(payload: dict) -> list[dict]:
    msgs: list[dict] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            msgs.extend(change.get("value", {}).get("messages", []))
    return msgs


def _raw(event: dict) -> bytes:
    body = event.get("body") or ""
    return base64.b64decode(body) if event.get("isBase64Encoded") else body.encode("utf-8")


def handler(event: dict, context: object) -> dict:
    metodo = event.get("requestContext", {}).get("http", {}).get("method", "")
    if metodo == "GET":
        qs = event.get("queryStringParameters") or {}
        esperado = secrets.leer(os.environ["META_VERIFY_TOKEN_PARAM"], descifrar=True)
        return responder_verificacion(
            qs.get("hub.mode", ""),
            qs.get("hub.verify_token", ""),
            qs.get("hub.challenge", ""),
            esperado,
        )

    raw = _raw(event)
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    app_secret = secrets.leer(os.environ["META_APP_SECRET_PARAM"], descifrar=True)
    if not firma_valida(app_secret, raw, headers.get("x-hub-signature-256", "")):
        return {"statusCode": 403, "headers": {"Content-Type": "text/plain"}, "body": "Forbidden"}

    for msg in _mensajes(json.loads(raw or b"{}")):
        invocar_bot(_a_evento(msg))
    return {"statusCode": 200, "headers": {"Content-Type": "text/plain"}, "body": "OK"}
