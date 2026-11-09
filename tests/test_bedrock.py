"""Parseo del tool-use de Bedrock (formato de Flor) hacia una Extraccion."""

from datetime import UTC, date
from decimal import Decimal

from visible.adapters.outbound.extractor_bedrock import construir_system_prompt, parsear_respuesta
from visible.application.extractor import Contenido
from visible.domain.movimiento import Categoria

RECEPCION = date(2026, 11, 8)


def _resp(input_dict: dict) -> dict:
    return {
        "output": {
            "message": {
                "content": [{"toolUse": {"name": "registrar_movimientos", "input": input_dict}}]
            }
        }
    }


RESPUESTA = _resp(
    {
        "tipo_entrada": "cuaderno",
        "legible": True,
        "movimientos": [
            {
                "fecha": "2026-11-07",
                "texto_original": "vendí 3 polos 75 yape",
                "concepto": "3 polos",
                "monto": 75,
                "categoria": "ingreso",
                "subcategoria": "venta_yape",
                "por_cobrar": False,
                "confianza": 0.95,
            },
            {
                "fecha": "2025-01-01",
                "texto_original": "compra tela 120",
                "concepto": "tela",
                "monto": 120,
                "categoria": "gasto_negocio",
                "subcategoria": "mercaderia",
                "confianza": 0.8,
            },
        ],
        "preguntas": [
            {
                "texto_original": "pasaje 6",
                "pregunta": "¿Negocio o personal?",
                "opciones": ["Negocio", "Personal"],
            }
        ],
        "alertas": ["monto_inusual"],
    }
)


def test_parseo_extraccion():
    ext = parsear_respuesta(RESPUESTA, RECEPCION)
    assert ext.legible is True
    assert ext.tipo_entrada == "cuaderno"
    assert len(ext.movimientos) == 2
    m0 = ext.movimientos[0]
    assert m0.monto == Decimal("75")
    assert m0.categoria is Categoria.INGRESO
    assert m0.origen == "yape"  # subcategoria venta_yape
    assert m0.tipo_entrada == "cuaderno"
    # fecha de 2025 (>60 días) se normaliza a la recepción
    assert ext.movimientos[1].fecha == RECEPCION
    assert ext.movimientos[1].origen == "efectivo"
    assert len(ext.preguntas) == 1
    assert ext.alertas == ["monto_inusual"]


def test_parseo_captura_yape():
    ext = parsear_respuesta(
        _resp(
            {
                "tipo_entrada": "yape",
                "legible": True,
                "movimientos": [
                    {
                        "fecha": "2026-11-08",
                        "texto_original": "Te yapeó María S/ 50",
                        "concepto": "Yape de María",
                        "monto": 50,
                        "categoria": "ingreso",
                        "subcategoria": "venta_yape",
                        "confianza": 0.97,
                    }
                ],
            }
        ),
        RECEPCION,
    )
    assert ext.tipo_entrada == "yape"
    m = ext.movimientos[0]
    assert m.categoria is Categoria.INGRESO
    assert m.subcategoria == "venta_yape"
    assert m.origen == "yape"
    assert m.tipo_entrada == "yape"
    assert m.concepto == "Cobro por Yape"  # sin nombres de terceros


def test_parseo_origen_yape_por_texto():
    ext = parsear_respuesta(
        _resp(
            {
                "legible": True,
                "movimientos": [
                    {
                        "fecha": "2026-11-08",
                        "texto_original": "casacas cobrado por yape 240",
                        "concepto": "2 casacas",
                        "monto": 240,
                        "categoria": "ingreso",
                        "subcategoria": "venta_efectivo",
                        "confianza": 0.9,
                    }
                ],
            }
        ),
        RECEPCION,
    )
    assert ext.movimientos[0].origen == "yape"  # "yape" en el texto


def test_sin_tooluse_ilegible():
    ext = parsear_respuesta({"output": {"message": {"content": [{"text": "hola"}]}}}, RECEPCION)
    assert ext.legible is False
    assert ext.movimientos == []


def test_system_prompt_inyecta_fecha_y_conceptos(tmp_path, monkeypatch):
    from datetime import datetime

    monkeypatch.setenv("PROMPT_EXTRACCION", "")  # usa el prompt empaquetado
    contenido = Contenido(conceptos=("pasaje = gasto_negocio",))
    recepcion = datetime(2026, 11, 8, 9, 30, tzinfo=UTC)
    prompt = construir_system_prompt(contenido, recepcion)
    assert "Fecha y hora de recepción: 2026-11-08 09:30 (America/Lima)" in prompt
    assert "pasaje = gasto_negocio" in prompt
    assert "Yape" in prompt
