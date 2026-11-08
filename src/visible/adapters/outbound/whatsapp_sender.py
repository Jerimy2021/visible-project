"""Adaptador outbound: envío de mensajes vía Meta WhatsApp Cloud API (Graph API).

Implementa el puerto `Mensajero`. Usa urllib (sin dependencias externas).
"""

import json
import os
import urllib.request

from visible.adapters.outbound import graph, secrets


class WhatsAppSender:
    """Envía texto por la Cloud API: POST /{phone_number_id}/messages."""

    def enviar_texto(self, telefono: str, texto: str) -> None:
        version = os.environ.get("GRAPH_API_VERSION", "v25.0")
        phone_id = secrets.leer(os.environ["META_PHONE_NUMBER_ID_PARAM"])
        url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
        cuerpo = json.dumps(
            {
                "messaging_product": "whatsapp",
                "to": telefono,
                "type": "text",
                "text": {"body": texto},
            }
        ).encode("utf-8")

        def enviar(token: str) -> None:
            req = urllib.request.Request(
                url,
                data=cuerpo,
                method="POST",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310 (host fijo Meta)
                resp.read()

        graph.ejecutar(os.environ["META_ACCESS_TOKEN_PARAM"], enviar)
