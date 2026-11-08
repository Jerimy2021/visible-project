"""Parseo del tool-use de la respuesta Converse de Bedrock (puro, sin AWS)."""

from decimal import Decimal

from visible.adapters.outbound.extractor_bedrock import parsear_respuesta
from visible.domain.movimiento import TipoMovimiento

RESPUESTA = {
    "output": {
        "message": {
            "role": "assistant",
            "content": [
                {
                    "toolUse": {
                        "name": "registrar_movimientos",
                        "input": {
                            "movimientos": [
                                {
                                    "fecha": "2026-11-08",
                                    "monto": 45.5,
                                    "concepto": "3 blusas",
                                    "tipo": "venta",
                                    "confianza": 0.9,
                                },
                                {
                                    "fecha": "2026-11-08",
                                    "monto": 120,
                                    "concepto": "compra de tela",
                                    "tipo": "gasto_negocio",
                                    "confianza": 0.7,
                                },
                            ]
                        },
                    }
                }
            ],
        }
    }
}


def test_parseo_tool_use():
    movs = parsear_respuesta(RESPUESTA)
    assert len(movs) == 2
    assert movs[0].monto == Decimal("45.5")
    assert movs[0].tipo is TipoMovimiento.VENTA
    assert movs[1].tipo is TipoMovimiento.GASTO_NEGOCIO
    assert movs[1].monto == Decimal("120")


def test_parseo_sin_tooluse_devuelve_vacio():
    assert parsear_respuesta({"output": {"message": {"content": [{"text": "hola"}]}}}) == []
