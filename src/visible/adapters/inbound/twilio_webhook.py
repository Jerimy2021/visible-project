"""Adaptador inbound: webhook de Twilio WhatsApp sobre API Gateway HttpApi (v2.0).

Valida X-Twilio-Signature (HMAC-SHA1, sin SDK de Twilio) y responde TwiML de eco.
"""

import base64
import hashlib
import hmac
from html import escape
from urllib.parse import parse_qsl

from visible.adapters.outbound import secrets
from visible.application.eco import construir_eco
from visible.domain.mensaje import MensajeEntrante

# --- Validación de firma ---------------------------------------------------


def firmar(url: str, params: dict[str, str], token: str) -> str:
    """Firma al estilo Twilio: URL + (clave+valor) ordenados por clave, HMAC-SHA1, base64."""
    data = url
    for clave in sorted(params):
        data += clave + params[clave]
    mac = hmac.new(token.encode("utf-8"), data.encode("utf-8"), hashlib.sha1)
    return base64.b64encode(mac.digest()).decode("ascii")


def firma_valida(url: str, params: dict[str, str], firma: str, token: str) -> bool:
    """Compara la firma esperada con la recibida en tiempo constante."""
    return hmac.compare_digest(firmar(url, params, token), firma)


# --- Handler ---------------------------------------------------------------


def _parsear_evento(event: dict) -> tuple[str, dict[str, str], str]:
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    params = dict(parse_qsl(body, keep_blank_values=True))
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    host = event.get("requestContext", {}).get("domainName") or headers.get("host", "")
    url = f"https://{host}{event.get('rawPath', '')}"
    firma = headers.get("x-twilio-signature", "")
    return url, params, firma


def _a_mensaje(params: dict[str, str]) -> MensajeEntrante:
    num_media = int(params.get("NumMedia", "0") or "0")
    medios = tuple(
        (params.get(f"MediaUrl{i}", ""), params.get(f"MediaContentType{i}", ""))
        for i in range(num_media)
    )
    return MensajeEntrante(
        telefono=params.get("From", ""),
        texto=params.get("Body", ""),
        medios=medios,
    )


def _twiml(texto: str) -> dict:
    cuerpo = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Message>{escape(texto)}</Message></Response>"
    )
    return {"statusCode": 200, "headers": {"Content-Type": "text/xml"}, "body": cuerpo}


def handler(event: dict, context: object) -> dict:
    url, params, firma = _parsear_evento(event)
    token = secrets.obtener_token()
    if not firma_valida(url, params, firma, token):
        return {
            "statusCode": 403,
            "headers": {"Content-Type": "text/plain"},
            "body": "Firma invalida",
        }
    return _twiml(construir_eco(_a_mensaje(params)))
