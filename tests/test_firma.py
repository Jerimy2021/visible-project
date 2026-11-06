"""Validación de firma con el vector conocido de la documentación de Twilio."""

from visible.adapters.inbound.twilio_webhook import firma_valida, firmar

URL = "https://mycompany.com/myapp.php?foo=1&bar=2"
PARAMS = {
    "CallSid": "CA1234567890ABCDE",
    "Caller": "+14158675309",
    "Digits": "1234",
    "From": "+14158675309",
    "To": "+18005551212",
}
TOKEN = "12345"
FIRMA = "RSOYDt4T1cUTdK1PDd93/VVr8B8="


def test_firma_vector_conocido():
    assert firmar(URL, PARAMS, TOKEN) == FIRMA


def test_firma_valida_acepta():
    assert firma_valida(URL, PARAMS, FIRMA, TOKEN)


def test_firma_valida_rechaza():
    assert not firma_valida(URL, PARAMS, "firmaIncorrecta=", TOKEN)
