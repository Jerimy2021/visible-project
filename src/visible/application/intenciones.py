"""Intenciones de texto del asistente (reglas simples, sin IA ni AWS).

Todo lo que no sea una de estas intenciones se trata como un registro
("vendí 3 polos a 25") y va al extractor.
"""

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

MENU = "menu"
RESUMEN = "resumen"
ALCANZA = "alcanza"
MIS_DATOS = "mis_datos"
BORRAR = "borrar"
NEGOCIO = "negocio"
REGISTRO = "registro"


@dataclass(frozen=True)
class Intencion:
    nombre: str
    monto: Decimal | None = None


def _normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFD", (texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")  # quita tildes
    return re.sub(r"[¿?¡!.,;:]+", " ", t).strip()


def extraer_monto(texto: str) -> Decimal | None:
    """Primer monto del texto: "500", "S/ 1 500", "1,500", "1500.50", "mil" no."""
    m = re.search(r"(\d{1,3}(?:[ .,]\d{3})+|\d+)(?:[.,](\d{1,2}))?(?!\d)", texto or "")
    if not m:
        return None
    entero = re.sub(r"[ .,]", "", m.group(1))
    try:
        return Decimal(f"{entero}.{m.group(2)}" if m.group(2) else entero)
    except InvalidOperation:
        return None


_SALUDOS = {
    "hola",
    "holi",
    "buenas",
    "buenos dias",
    "buenas tardes",
    "buenas noches",
    "menu",
    "ayuda",
    "inicio",
    "opciones",
    "que puedes hacer",
    "hola visible",
}
_RESUMEN = ("resumen", "cuanto gane", "mi semana", "como me fue", "cuanto vendi")
_ALCANZA = ("me alcanza", "alcanza para", "puedo comprar", "me da para")
_BORRAR = (
    "borrar mis datos",
    "borra mis datos",
    "eliminar mis datos",
    "elimina mis datos",
    "borrar todo",
)
_NEGOCIO = ("ver mi negocio", "mi negocio", "mi panel", "mis tableros")


def detectar(texto: str) -> Intencion:
    t = _normalizar(texto)
    if not t:
        return Intencion(MENU)
    if any(p in t for p in _BORRAR):
        return Intencion(BORRAR)
    if "mis datos" in t:
        return Intencion(MIS_DATOS)
    if any(p in t for p in _ALCANZA):
        return Intencion(ALCANZA, extraer_monto(texto))
    if any(p in t for p in _RESUMEN):
        return Intencion(RESUMEN)
    if t in _SALUDOS or (len(t.split()) <= 3 and t.split()[0] in {"hola", "buenas", "menu"}):
        return Intencion(MENU)
    if t in _NEGOCIO:
        return Intencion(NEGOCIO)
    return Intencion(REGISTRO)


def responder_alcanza(monto: Decimal | None, ahorro_semana: Decimal, soles) -> str:
    """Respuesta a "¿me alcanza para X?" comparando con el ahorro de los últimos 7 días."""
    if monto is None or monto <= 0:
        return '¿Para cuánto quieres comprar? Escríbeme, por ejemplo:\n"me alcanza para 500"'
    if ahorro_semana <= 0:
        return (
            f"Esta semana todavía no tienes ahorro registrado, así que {soles(monto)} "
            "no saldría de tu ganancia. Registra tus ventas y gastos y lo vemos de nuevo 💪"
        )
    if monto <= ahorro_semana:
        return (
            f"Sí te alcanza ✓\nEsta semana ahorraste {soles(ahorro_semana)}.\n"
            f"Si gastas {soles(monto)}, te quedan {soles(ahorro_semana - monto)}."
        )
    return (
        f"Todavía no 🙏\nEsta semana ahorraste {soles(ahorro_semana)} y te faltan "
        f"{soles(monto - ahorro_semana)}.\nPuedes comprar una parte ahora o esperar unos días."
    )
