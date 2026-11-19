"""Normalización de valores de los CSV de SharePoint."""

import unicodedata
from decimal import Decimal, InvalidOperation

_VERDADEROS = {"verdadero", "sí", "si", "true", "1", "x"}
_FALSOS = {"falso", "no", "false", "0"}


def texto(valor: str | None) -> str:
    """Trim; 'N/A' (en cualquier variante) -> 'NA'."""
    v = (valor or "").strip()
    compacto = v.upper().replace(".", "").replace(" ", "").replace("/", "")
    return "NA" if compacto == "NA" else v


def booleano(valor: str | None) -> bool | None:
    """'Verdadero'/'Sí' -> True; 'Falso'/'No' -> False; vacío -> None."""
    v = (valor or "").strip().lower()
    if v in _VERDADEROS:
        return True
    if v in _FALSOS:
        return False
    return None


def numero(valor: str | None) -> Decimal | None:
    v = (valor or "").strip().replace(",", ".")
    if not v:
        return None
    try:
        return Decimal(v)
    except InvalidOperation:
        return None


_PUNTO = {
    "ok": "CUMPLE",
    "cumple": "CUMPLE",
    "p": "NO_CUMPLE",
    "no cumple": "NO_CUMPLE",
    "no_cumple": "NO_CUMPLE",
    "na": "NA",
    "n/a": "NA",
    "": "NA",
}


def punto(valor: str | None) -> str:
    """OK/Cumple -> CUMPLE; P/No cumple -> NO_CUMPLE; NA/N/A/vacío -> NA."""
    return _PUNTO.get((valor or "").strip().lower(), "NA")


def nombre_canonico(valor: str | None) -> str:
    """Minúsculas, sin tildes, espacios colapsados — para unificar alias de personas."""
    v = unicodedata.normalize("NFKD", (valor or "").strip().lower())
    v = "".join(c for c in v if not unicodedata.combining(c))
    return " ".join(v.split())
