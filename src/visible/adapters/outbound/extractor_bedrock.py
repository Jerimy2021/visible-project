"""Extractor con Amazon Bedrock (Converse + tool use, salida JSON forzada).

El parseo de la respuesta (`parsear_respuesta`) es puro y testeable sin AWS.
"""

import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from visible.application.extractor import Contenido, Extraccion, Pregunta
from visible.domain.movimiento import Categoria, Movimiento, normalizar_fecha

MODELO_DEFECTO = "us.anthropic.claude-sonnet-4-6"
MODELO_RESPALDO = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
HERRAMIENTA = "registrar_movimientos"
LIMA = timezone(timedelta(hours=-5))  # America/Lima (sin DST)

_MOVIMIENTO = {
    "type": "object",
    "properties": {
        "fecha": {"type": "string", "description": "AAAA-MM-DD"},
        "texto_original": {"type": "string"},
        "concepto": {"type": "string"},
        "cantidad": {"type": "number"},
        "precio_unitario": {"type": "number"},
        "monto": {"type": "number", "description": "en soles"},
        "moneda": {"type": "string", "enum": ["PEN", "USD"]},
        "categoria": {"type": "string", "enum": [c.value for c in Categoria]},
        "subcategoria": {"type": "string"},
        "por_cobrar": {"type": "boolean"},
        "confianza": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["fecha", "concepto", "monto", "categoria", "confianza"],
}

_PREGUNTA = {
    "type": "object",
    "properties": {
        "texto_original": {"type": "string"},
        "pregunta": {"type": "string"},
        "opciones": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["pregunta", "opciones"],
}

TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "tipo_entrada": {"type": "string", "enum": ["cuaderno", "yape", "texto"]},
        "fecha_foto": {"type": "string"},
        "legible": {"type": "boolean"},
        "movimientos": {"type": "array", "items": _MOVIMIENTO},
        "preguntas": {"type": "array", "items": _PREGUNTA},
        "alertas": {"type": "array", "items": {"type": "string"}},
        "total_escrito_en_cuaderno": {"type": "number"},
        "cuadra_con_total": {"type": "boolean"},
    },
    "required": ["legible", "movimientos"],
}

_MIME_EXT = {"image/jpeg": "jpeg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}


def _cargar_prompt() -> str:
    ruta = os.environ.get("PROMPT_EXTRACCION")
    candidatas = [Path(ruta)] if ruta else []
    base = Path(__file__).resolve()
    candidatas += [p / "prompts" / "extraccion_cuaderno.md" for p in base.parents]
    for c in candidatas:
        if c.is_file():
            return c.read_text(encoding="utf-8")
    raise FileNotFoundError("No se encontró prompts/extraccion_cuaderno.md")


def construir_system_prompt(contenido: Contenido, recepcion: datetime) -> str:
    """Reemplaza los placeholders {fecha_recepcion} y {conceptos_aprendidos} del prompt."""
    conceptos = "; ".join(contenido.conceptos) if contenido.conceptos else "ninguno todavía"
    return (
        _cargar_prompt()
        .replace("{fecha_recepcion}", recepcion.strftime("%Y-%m-%d %H:%M"))
        .replace("{conceptos_aprendidos}", conceptos)
    )


def _tool_input(respuesta: dict) -> dict | None:
    for bloque in respuesta.get("output", {}).get("message", {}).get("content", []):
        uso = bloque.get("toolUse")
        if uso and uso.get("name") == HERRAMIENTA:
            return uso.get("input", {})
    return None


def _origen(item: dict, tipo_entrada: str = "") -> str:
    """ "yape" solo si viene de una captura de Yape (verificable).

    Si el cuaderno o el texto dicen "yape", es una venta por Yape declarada:
    "yape_anotado" (no cuenta como verificada en el puntaje).
    """
    if tipo_entrada == "yape":
        return "yape"
    texto = f"{item.get('texto_original', '')} {item.get('concepto', '')}".lower()
    if item.get("subcategoria") == "venta_yape" or "yape" in texto:
        return "yape_anotado"
    return "efectivo"


def _a_movimiento(item: dict, recepcion: date, tipo_entrada: str = "") -> Movimiento:
    try:
        monto = Decimal(str(item["monto"]))
    except (InvalidOperation, KeyError, TypeError):
        monto = Decimal(0)
    try:
        fecha = normalizar_fecha(date.fromisoformat(item["fecha"]), recepcion)
    except (ValueError, KeyError, TypeError):
        fecha = recepcion
    try:
        categoria = Categoria(item.get("categoria", "por_clasificar"))
    except ValueError:
        categoria = Categoria.POR_CLASIFICAR
    concepto = item.get("concepto", "")
    # Captura de Yape: concepto genérico, nunca nombres de terceros.
    if tipo_entrada == "yape":
        concepto = "Cobro por Yape" if categoria is Categoria.INGRESO else "Pago por Yape"
    return Movimiento(
        fecha=fecha,
        monto=monto,
        concepto=concepto,
        categoria=categoria,
        subcategoria=item.get("subcategoria", ""),
        confianza=float(item.get("confianza", 0.0)),
        origen=_origen(item, tipo_entrada),
        por_cobrar=bool(item.get("por_cobrar", False)),
        tipo_entrada=tipo_entrada,
    )


def parsear_respuesta(respuesta: dict, recepcion: date | None = None) -> Extraccion:
    """Convierte la respuesta Converse (tool use) en una Extraccion del dominio."""
    recepcion = recepcion or datetime.now(LIMA).date()
    uso = _tool_input(respuesta)
    if uso is None:
        return Extraccion(legible=False)
    tipo_entrada = uso.get("tipo_entrada", "")
    movimientos = [_a_movimiento(m, recepcion, tipo_entrada) for m in uso.get("movimientos", [])]
    preguntas = [
        Pregunta(
            texto_original=p.get("texto_original", ""),
            pregunta=p.get("pregunta", ""),
            opciones=tuple(p.get("opciones", [])),
        )
        for p in uso.get("preguntas", [])
    ]
    return Extraccion(
        movimientos=movimientos,
        legible=bool(uso.get("legible", True)),
        preguntas=preguntas,
        alertas=list(uso.get("alertas", [])),
        tipo_entrada=tipo_entrada,
    )


class BedrockExtractor:
    """Invoca Converse con bloque de imagen y herramienta de salida.

    Usa `modelo` y, si falla, reintenta una vez con `respaldo`.
    """

    def __init__(self, modelo: str | None = None, respaldo: str | None = None) -> None:
        self.modelo = modelo or os.environ.get("MODEL_ID", MODELO_DEFECTO)
        self.respaldo = respaldo or os.environ.get("MODEL_ID_FALLBACK", MODELO_RESPALDO)

    def _bloques(self, contenido: Contenido) -> list[dict]:
        bloques: list[dict] = []
        if contenido.imagen is not None:
            fmt = _MIME_EXT.get(contenido.mime_type, "jpeg")
            bloques.append({"image": {"format": fmt, "source": {"bytes": contenido.imagen}}})
        bloques.append(
            {"text": contenido.texto or "Extrae los movimientos de esta foto del cuaderno."}
        )
        return bloques

    def _converse(self, cliente, modelo: str, bloques: list[dict], system: str) -> dict:
        return cliente.converse(
            modelId=modelo,
            system=[{"text": system}],
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

    def extraer(self, contenido: Contenido) -> Extraccion:
        import boto3

        recepcion = datetime.now(LIMA)
        system = construir_system_prompt(contenido, recepcion)
        cliente = boto3.client("bedrock-runtime")
        bloques = self._bloques(contenido)
        modelos = [self.modelo] + ([self.respaldo] if self.respaldo != self.modelo else [])
        for i, modelo in enumerate(modelos):
            try:
                resp = self._converse(cliente, modelo, bloques, system)
                return parsear_respuesta(resp, recepcion.date())
            except Exception:
                if i == len(modelos) - 1:
                    raise
        return Extraccion(legible=False)
