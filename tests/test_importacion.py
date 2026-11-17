from decimal import Decimal
from pathlib import Path

from visible.domain.importacion import TABLAS, parsear, tabla_de_archivo
from visible.domain.usuarios import INSPECTOR_PILOTO

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def _parsear(logico: str):
    return parsear(logico, (RAW / TABLAS[logico][0]).read_bytes())


def test_tabla_de_archivo():
    assert tabla_de_archivo("uploads/MantenimientosMensuales.csv") == "mantenimientos"
    assert tabla_de_archivo("Extintores.csv") == "extintores"
    assert tabla_de_archivo("cualquiera.csv") == ""


def test_sites():
    items, errores = _parsear("sites")
    assert errores == []
    assert len(items) == 1
    s = items[0]
    assert s["codigo"] == "HUA"
    assert s["activo"] is True
    assert s["supervisor_ssoma"] == "Jose Manuel Chanta Torres"


def test_extintores():
    items, errores = _parsear("extintores")
    assert errores == []
    assert len(items) == 49
    e = next(x for x in items if x["codigo"] == "HUA-00001")
    assert e["inspector_asignado"] == INSPECTOR_PILOTO  # piloto: todos a José Manuel
    assert e["ph_por_confirmar"] is True
    assert e["activo"] is True
    assert e["capacidad"] == Decimal("20")
    assert e["fecha_fabricacion"] == "2017-01-01"
    assert e["fecha_prox_mant_mensual"] == "2026-12-15"


def test_mantenimientos():
    items, errores = _parsear("mantenimientos")
    assert errores == []
    assert len(items) == 434
    m = items[0]
    assert m["codigo"] == "HUA-00002"
    assert m["periodo"] == "2026-01"
    assert m["gabinete"] == "NA"  # "N/A" normalizado
    assert m["cantidad_p"] == 0
    assert m["site"] == "HUA"


def test_aprobaciones():
    items, errores = _parsear("aprobaciones")
    assert errores == []
    assert len(items) == 1
    a = items[0]
    assert a["site"] == "HUA"
    assert a["periodo"] == "2026-10"
    assert a["estado"] == "Devuelto"
