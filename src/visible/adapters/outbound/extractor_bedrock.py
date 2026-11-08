"""Extractor con Amazon Bedrock (Converse + tool use, salida JSON forzada).

El parseo de la respuesta (`parsear_respuesta`) es puro y testeable sin AWS.
"""

import os
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from visible.application.extractor import Contenido
from visible.domain.movimiento import Movimiento, TipoMovimiento

MODELO_DEFECTO = "us.anthropic.claude-sonnet-5-5"
HERRAMIENTA = "registrar_movimientos"

# Esquema JSON que fuerza la forma de la salida del modelo.
TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "movimientos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "fecha": {"type": "string", "description": "YYYY-MM-DD"},
                    "monto": {"type": "number", "description": "en soles"},
                    "concepto": {"type": "string"},
                    "tipo": {
                        "type": "string",
                        "enum": [t.value for t in TipoMovimiento],
                    },
                    "confianza": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["fecha", "monto", "concepto", "tipo", "confianza"],
            },
        }
    },
    "required": ["movimientos"],
}

_MIME_EXT = {"image/jpeg": "jpeg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}


def _cargar_prompt() -> str:
    ruta = os.environ.get("PROMPT_EXTRACCION")
    candidatas = [Path(ruta)] if ruta else []
    # Busca prompts/extraccion_cuaderno.md subiendo desde este archivo.
    base = Path(__file__).resolve()
    candidatas += [p / "prompts" / "extraccion_cuaderno.md" for p in base.parents]
    for c in candidatas:
        if c.is_file():
            return c.read_text(encoding="utf-8")
    raise FileNotFoundError("No se encontró prompts/extraccion_cuaderno.md")


def parsear_respuesta(respuesta: dict) -> list[Movimiento]:
    """Extrae los movimientos del bloque toolUse de una respuesta Converse."""
    contenido = respuesta.get("output", {}).get("message", {}).get("content", [])
    for bloque in contenido:
        uso = bloque.get("toolUse")
        if uso and uso.get("name") == HERRAMIENTA:
            return [_a_movimiento(m) for m in uso.get("input", {}).get("movimientos", [])]
    return []


def _a_movimiento(item: dict) -> Movimiento:
    try:
        monto = Decimal(str(item["monto"]))
    except (InvalidOperation, KeyError):
        monto = Decimal(0)
    return Movimiento(
        fecha=date.fromisoformat(item["fecha"]),
        monto=monto,
        concepto=item.get("concepto", ""),
        tipo=TipoMovimiento(item["tipo"]),
        confianza=float(item.get("confianza", 0.0)),
    )


class BedrockExtractor:
    """Invoca Converse con bloque de imagen y herramienta de salida."""

    def __init__(self, modelo: str | None = None) -> None:
        self.modelo = modelo or os.environ.get("BEDROCK_MODEL_ID", MODELO_DEFECTO)

    def extraer(self, contenido: Contenido) -> list[Movimiento]:
        import boto3

        bloques: list[dict] = []
        if contenido.imagen is not None:
            fmt = _MIME_EXT.get(contenido.mime_type, "jpeg")
            bloques.append({"image": {"format": fmt, "source": {"bytes": contenido.imagen}}})
        texto = contenido.texto or "Extrae los movimientos de esta foto del cuaderno."
        bloques.append({"text": texto})

        cliente = boto3.client("bedrock-runtime")
        respuesta = cliente.converse(
            modelId=self.modelo,
            system=[{"text": _cargar_prompt()}],
            messages=[{"role": "user", "content": bloques}],
            toolConfig={
                "tools": [
                    {
                        "toolSpec": {
                            "name": HERRAMIENTA,
                            "description": "Registra los movimientos leídos del cuaderno.",
                            "inputSchema": {"json": TOOL_SCHEMA},
                        }
                    }
                ],
                "toolChoice": {"tool": {"name": HERRAMIENTA}},
            },
        )
        return parsear_respuesta(respuesta)
