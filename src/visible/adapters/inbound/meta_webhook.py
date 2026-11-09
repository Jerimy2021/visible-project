"""Adaptador inbound: webhook de Meta WhatsApp Cloud API sobre HttpApi (v2.0).

GET  /webhook -> verificación del webhook (hub.challenge).
POST /webhook -> notificaciones de mensajes, validadas con X-Hub-Signature-256.
"""

import base64
import hashlib
import hmac
import json
import os

from visible.adapters.outbound import secrets
from visible.adapters.outbound.invocador import invocar_procesar
from visible.domain.mensaje import MensajeEntrante, a_dict

# --- Firma (X-Hub-Signature-256) ------------------------------------------


def firmar(app_secret: str, raw: bytes) -> str:
    """Firma estilo Meta: 'sha256=' + HMAC-SHA256(app_secret, bytes crudos del body)."""
    mac = hmac.new(app_secret.encode("utf-8"), raw, hashlib.sha256)
    return "sha256=" + mac.hexdigest()


def firma_valida(app_secret: str, raw: bytes, cabecera: str) -> bool:
    """Compara en tiempo constante la firma esperada con el header recibido."""
    return hmac.compare_digest(firmar(app_secret, raw), cabecera or "")


# --- Verificación GET ------------------------------------------------------


def responder_verificacion(
    mode: str, token_recibido: str, challenge: str, token_esperado: str
) -> dict:
    """Devuelve el challenge en text/plain si mode=subscribe y el token coincide."""
    if mode == "subscribe" and hmac.compare_digest(token_recibido or "", token_esperado):
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/plain"},
            "body": challenge or "",
        }
    return {"statusCode": 403, "headers": {"Content-Type": "text/plain"}, "body": "Forbidden"}


# --- Parseo de mensajes ----------------------------------------------------

_TIPOS_MEDIA = ("image", "audio", "document", "video", "sticker")


def parsear_mensajes(payload: dict) -> list[MensajeEntrante]:
    """Extrae los mensajes entrantes. Ignora notificaciones de `statuses`."""
    mensajes: list[MensajeEntrante] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                mensajes.append(_a_mensaje(msg))
    return mensajes


def _a_mensaje(msg: dict) -> MensajeEntrante:
    telefono = msg.get("from", "")
    tipo = msg.get("type", "")
    mensaje_id = msg.get("id", "")
    if tipo == "text":
        return MensajeEntrante(
            telefono=telefono,
            texto=msg.get("text", {}).get("body", ""),
            mensaje_id=mensaje_id,
        )
    if tipo in _TIPOS_MEDIA:
        media = msg.get(tipo, {})
        medios = ((media.get("id", ""), media.get("mime_type", "")),)
        return MensajeEntrante(
            telefono=telefono,
            texto=media.get("caption", ""),
            medios=medios,
            mensaje_id=mensaje_id,
        )
    return MensajeEntrante(telefono=telefono, texto="", mensaje_id=mensaje_id)


# --- Handler ---------------------------------------------------------------


def _raw_body(event: dict) -> bytes:
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        return base64.b64decode(body)
    return body.encode("utf-8")


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

    raw = _raw_body(event)
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    app_secret = secrets.leer(os.environ["META_APP_SECRET_PARAM"], descifrar=True)
    if not firma_valida(app_secret, raw, headers.get("x-hub-signature-256", "")):
        return {"statusCode": 403, "headers": {"Content-Type": "text/plain"}, "body": "Forbidden"}

    payload = json.loads(raw or b"{}")
    # Responde 200 rápido e invoca el procesamiento async (Bedrock/descarga tardan).
    for msg in _mensajes_crudos(payload):
        invocar_procesar(_a_evento(msg))
    return {"statusCode": 200, "headers": {"Content-Type": "text/plain"}, "body": "OK"}


def _mensajes_crudos(payload: dict) -> list[dict]:
    msgs: list[dict] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            msgs.extend(change.get("value", {}).get("messages", []))
    return msgs


def _a_evento(msg: dict) -> dict:
    """Payload async: respuesta de botón/lista -> clasificación; si no, mensaje normal."""
    if msg.get("type") == "interactive":
        inter = msg.get("interactive", {})
        reply = inter.get("button_reply") or inter.get("list_reply") or {}
        return {
            "clasificacion": reply.get("id", ""),
            "telefono": msg.get("from", ""),
            "mensaje_id": msg.get("id", ""),
        }
    return a_dict(_a_mensaje(msg))
