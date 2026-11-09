"""Adaptador outbound: envío de mensajes vía Meta WhatsApp Cloud API (Graph API).

Implementa el puerto `Mensajero`. Usa urllib (sin dependencias externas).
"""

import json
import os
import urllib.request

from visible.adapters.outbound import graph, secrets


class WhatsAppSender:
    """Envía texto y mensajes interactivos por la Cloud API."""

    def _enviar(self, payload: dict) -> None:
        version = os.environ.get("GRAPH_API_VERSION", "v25.0")
        phone_id = secrets.leer(os.environ["META_PHONE_NUMBER_ID_PARAM"])
        url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
        cuerpo = json.dumps({"messaging_product": "whatsapp", **payload}).encode("utf-8")

        def post(token: str) -> None:
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

        graph.ejecutar(os.environ["META_ACCESS_TOKEN_PARAM"], post)

    def enviar_texto(self, telefono: str, texto: str) -> None:
        self._enviar({"to": telefono, "type": "text", "text": {"body": texto}})

    def enviar_opciones(self, telefono: str, texto: str, opciones: list[tuple[str, str]]) -> None:
        """Botones si hay <=3 opciones; si hay más, mensaje de lista."""
        if len(opciones) <= 3:
            interactivo = {
                "type": "button",
                "body": {"text": texto},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": id_, "title": titulo[:20]}}
                        for id_, titulo in opciones
                    ]
                },
            }
        else:
            interactivo = {
                "type": "list",
                "body": {"text": texto},
                "action": {
                    "button": "Elegir",
                    "sections": [
                        {
                            "title": "Opciones",
                            "rows": [
                                {"id": id_, "title": titulo[:24]} for id_, titulo in opciones[:10]
                            ],
                        }
                    ],
                },
            }
        self._enviar({"to": telefono, "type": "interactive", "interactive": interactivo})

    def enviar_link(self, telefono: str, texto: str, etiqueta: str, url: str) -> None:
        """Mensaje con un botón que abre una URL (interactive cta_url)."""
        self._enviar(
            {
                "to": telefono,
                "type": "interactive",
                "interactive": {
                    "type": "cta_url",
                    "body": {"text": texto},
                    "action": {
                        "name": "cta_url",
                        "parameters": {"display_text": etiqueta, "url": url},
                    },
                },
            }
        )
