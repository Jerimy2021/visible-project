"""Fechas en America/Lima y normalización de fechas de los CSV (dd/mm/aaaa)."""

from datetime import date, datetime, timedelta, timezone

LIMA = timezone(timedelta(hours=-5))  # America/Lima (sin DST)


def hoy_lima() -> date:
    return datetime.now(LIMA).date()


def normalizar_fecha(valor: str) -> str:
    """'dd/mm/aaaa[ hh:mm]' -> 'aaaa-mm-dd'. Vacío o ilegible -> ''."""
    v = (valor or "").strip()
    if not v:
        return ""
    fecha = v.split(" ", 1)[0]  # descarta la hora si viene
    for sep in ("/", "-"):
        partes = fecha.split(sep)
        if len(partes) == 3:
            try:
                d, m, a = (int(p) for p in partes)
                if a < 100:  # por si viniera aa
                    a += 2000
                return date(a, m, d).isoformat()
            except ValueError:
                return ""
    return ""
