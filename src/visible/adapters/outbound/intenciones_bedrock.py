"""Clasificación de intención con Amazon Bedrock (Claude Haiku).

Bedrock SOLO entiende la pregunta; los datos salen del dominio/API, nunca del modelo.
`parsear_intencion` es puro y testeable sin AWS.
"""

import os

MODELO = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
HERRAMIENTA = "responder_intencion"
INTENCIONES = ["faltan", "donde", "p_abiertos", "resumen", "ya_termine", "otro"]

TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "intencion": {"type": "string", "enum": INTENCIONES},
        "codigo": {
            "type": "string",
            "description": "código de extintor si menciona uno, ej HUA-00012",
        },
    },
    "required": ["intencion"],
}

SYSTEM = (
    "Clasificas el mensaje de un inspector de extintores en una intención. "
    "faltan = cuántos le faltan por inspeccionar. donde = dónde está un extintor "
    "(extrae su código). p_abiertos = sus observaciones/P pendientes. resumen = avance "
    "del mes. ya_termine = dice que ya terminó o ya lo hizo. otro = cualquier otra cosa. "
    "Responde solo con la herramienta."
)


def parsear_intencion(respuesta: dict) -> dict:
    for bloque in respuesta.get("output", {}).get("message", {}).get("content", []):
        uso = bloque.get("toolUse")
        if uso and uso.get("name") == HERRAMIENTA:
            inp = uso.get("input", {})
            intencion = inp.get("intencion", "otro")
            if intencion not in INTENCIONES:
                intencion = "otro"
            return {"intencion": intencion, "codigo": (inp.get("codigo") or "").upper().strip()}
    return {"intencion": "otro", "codigo": ""}


def clasificar(texto: str) -> dict:
    import boto3

    cliente = boto3.client("bedrock-runtime")
    resp = cliente.converse(
        modelId=os.environ.get("MODEL_ID_BOT", MODELO),
        system=[{"text": SYSTEM}],
        messages=[{"role": "user", "content": [{"text": texto}]}],
        toolConfig={
            "tools": [
                {
                    "toolSpec": {
                        "name": HERRAMIENTA,
                        "description": "Clasifica la intención del inspector.",
                        "inputSchema": {"json": TOOL_SCHEMA},
                    }
                }
            ],
            "toolChoice": {"tool": {"name": HERRAMIENTA}},
        },
    )
    return parsear_intencion(resp)
