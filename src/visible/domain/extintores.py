"""Estado de inspección por extintor y helpers de alcance (reglas 05)."""

from datetime import date

HECHO = "HECHO"
ATRASADO = "ATRASADO"
POR_HACER = "POR HACER"


def en_alcance(extintor: dict, site: str) -> bool:
    """Activo y de la planta pedida ('Todas' = cualquiera)."""
    return bool(extintor.get("activo")) and (site == "Todas" or extintor.get("site") == site)


def estado_inspeccion(extintor: dict, mantenimientos: list[dict], periodo: str, hoy: date) -> str:
    """HECHO si ya tiene fila del periodo; si no, ATRASADO cuando venció la próxima
    fecha de mantenimiento; POR HACER en caso contrario."""
    if any(m.get("periodo") == periodo for m in mantenimientos):
        return HECHO
    prox = extintor.get("fecha_prox_mant_mensual") or ""
    if prox and date.fromisoformat(prox) < hoy:
        return ATRASADO
    return POR_HACER
