"""Webhook de Meta: firma, verificación GET y parseo de payloads."""

from visible.adapters.inbound.meta_webhook import (
    firma_valida,
    firmar,
    parsear_mensajes,
    responder_verificacion,
)

APP_SECRET = "s3cr3t-de-prueba"


def test_firma_valida_con_vector_generado():
    raw = b'{"object":"whatsapp_business_account"}'
    cabecera = firmar(APP_SECRET, raw)  # vector generado aquí mismo
    assert cabecera.startswith("sha256=")
    assert firma_valida(APP_SECRET, raw, cabecera)


def test_firma_rechaza_body_alterado():
    cabecera = firmar(APP_SECRET, b'{"a":1}')
    assert not firma_valida(APP_SECRET, b'{"a":2}', cabecera)


def test_verificacion_ok():
    resp = responder_verificacion("subscribe", "tok123", "CHALLENGE", "tok123")
    assert resp["statusCode"] == 200
    assert resp["body"] == "CHALLENGE"
    assert resp["headers"]["Content-Type"] == "text/plain"


def test_verificacion_token_incorrecto():
    resp = responder_verificacion("subscribe", "malo", "CHALLENGE", "tok123")
    assert resp["statusCode"] == 403


PAYLOAD_TEXTO = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "messages": [
                            {
                                "from": "51999888777",
                                "id": "wamid.ABC",
                                "type": "text",
                                "text": {"body": "Hola Visible"},
                            }
                        ],
                    }
                }
            ]
        }
    ],
}

PAYLOAD_IMAGEN = {
    "entry": [
        {
            "changes": [
                {
                    "value": {
                        "messages": [
                            {
                                "from": "51999888777",
                                "type": "image",
                                "image": {
                                    "id": "media-123",
                                    "mime_type": "image/jpeg",
                                    "caption": "mi venta",
                                },
                            }
                        ]
                    }
                }
            ]
        }
    ]
}

PAYLOAD_STATUS = {
    "entry": [{"changes": [{"value": {"statuses": [{"id": "wamid.X", "status": "delivered"}]}}]}]
}


def test_parseo_texto():
    msgs = parsear_mensajes(PAYLOAD_TEXTO)
    assert len(msgs) == 1
    assert msgs[0].telefono == "51999888777"
    assert msgs[0].texto == "Hola Visible"
    assert msgs[0].medios == ()


def test_parseo_imagen():
    msgs = parsear_mensajes(PAYLOAD_IMAGEN)
    assert len(msgs) == 1
    assert msgs[0].texto == "mi venta"
    assert msgs[0].medios == (("media-123", "image/jpeg"),)


def test_parseo_ignora_statuses():
    assert parsear_mensajes(PAYLOAD_STATUS) == []
