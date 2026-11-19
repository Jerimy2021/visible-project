from visible.adapters.inbound.meta_webhook import _a_evento, firma_valida, firmar
from visible.adapters.outbound.intenciones_bedrock import parsear_intencion
from visible.application import bot


def test_textos():
    assert "Te faltan 3" in bot.texto_faltan(
        3, [{"codigo": "HUA-1", "piso": "01", "ubicacion": "Pasillo"}]
    )
    assert "HUA-1" in bot.texto_faltan(
        3, [{"codigo": "HUA-1", "piso": "01", "ubicacion": "Pasillo"}]
    )
    assert bot.texto_donde(None, "HUA-9").startswith("No encontré")
    assert "Piso 01" in bot.texto_donde(
        {"codigo": "HUA-1", "piso": "01", "ubicacion": "X", "zona_brigada": "Z"}, "HUA-1"
    )
    assert "2 «No cumple»" in bot.texto_no_cumple(
        [{"codigo": "A", "puntos_p": ["Presión"]}, {"codigo": "B", "puntos_p": []}]
    )
    assert "José" in bot.texto_felicitacion("José Manuel", 5)
    assert "Jerson" in bot.texto_bienvenida("Jerson David Romero", es_admin=False)


def test_textos_admin():
    c = {
        "site": "HUA",
        "periodo": "2026-11",
        "avance_pct": 67,
        "inspeccionados": 2,
        "total": 3,
        "faltan": 1,
        "p_abiertos": 2,
        "conformes_1a_pct": 50,
        "aprobacion": {"estado": "Pendiente"},
    }
    assert "Avance 67%" in bot.texto_resumen_admin(c)
    assert "José: 2/3" in bot.texto_equipo(
        [{"inspector": "José Manuel", "hechos": 2, "asignados": 3}]
    )
    a = bot.texto_alertas([{"codigo": "HUA-2", "puntos_p": ["Presión"]}], 4)
    assert "1 «No cumple» abiertos · 4 atrasados" in a
    assert [b[0] for b in bot.MENU_ADMIN] == [
        "adm|resumen",
        "adm|equipo",
        "adm|alertas",
        "adm|nocumple",
        "adm|obs",
    ]
    assert "No cumplieron en HUA (2026-10): 1" in bot.texto_no_cumplieron(
        "HUA", "2026-10", [{"codigo": "HUA-5", "puntos": ["Presión"], "levantado": False}]
    )


def test_parsear_intencion():
    def resp(inp):
        return {
            "output": {
                "message": {"content": [{"toolUse": {"name": "responder_intencion", "input": inp}}]}
            }
        }

    assert parsear_intencion(resp({"intencion": "faltan"})) == {
        "intencion": "faltan",
        "codigo": "",
        "site": "",
        "mes": "",
    }
    r = parsear_intencion(
        resp({"intencion": "no_cumplieron", "codigo": "hua-00012", "site": "fid", "mes": "Octubre"})
    )
    assert r == {
        "intencion": "no_cumplieron",
        "codigo": "HUA-00012",
        "site": "FID",
        "mes": "octubre",
    }
    assert parsear_intencion(resp({"intencion": "raro"}))["intencion"] == "otro"
    assert parsear_intencion({"output": {"message": {"content": []}}})["intencion"] == "otro"


def test_webhook_evento():
    texto = {"from": "51999", "id": "wamid.1", "type": "text", "text": {"body": "hola"}}
    assert _a_evento(texto) == {
        "telefono": "51999",
        "boton": "",
        "texto": "hola",
        "mensaje_id": "wamid.1",
    }
    boton = {
        "from": "51999",
        "id": "wamid.2",
        "type": "interactive",
        "interactive": {
            "type": "button_reply",
            "button_reply": {"id": "bot|faltan", "title": "Cuántos me faltan"},
        },
    }
    assert _a_evento(boton)["boton"] == "bot|faltan"


def test_webhook_firma():
    raw = b'{"object":"x"}'
    assert firma_valida("secreto", raw, firmar("secreto", raw))
    assert not firma_valida("secreto", raw, "sha256=mala")
