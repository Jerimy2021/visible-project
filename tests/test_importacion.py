from decimal import Decimal
from pathlib import Path

from visible.domain.importacion import TABLAS, parsear, separar_observacion, tabla_de_archivo

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def _parsear(logico: str):
    return parsear(logico, (RAW / TABLAS[logico][0]).read_bytes())


def test_tabla_de_archivo():
    assert tabla_de_archivo("uploads/MantenimientosMensuales.csv") == "mantenimientos"
    assert tabla_de_archivo("Extintores.csv") == "extintores"
    assert tabla_de_archivo("cualquiera.csv") == ""


def test_separar_observacion():
    notas, adic, general = separar_observacion(
        "9.PRUEBA | ok · Adicionales: extra · RESERVA ALICORP"
    )
    assert notas == "9.PRUEBA | ok"
    assert adic == "Adicionales: extra"
    assert general == "RESERVA ALICORP"


def test_sites():
    items, errores = _parsear("sites")
    assert errores == []
    assert len(items) == 2
    assert {s["codigo"] for s in items} == {"HUA", "FID"}


def test_extintores():
    items, errores = _parsear("extintores")
    assert errores == []
    assert len(items) == 128
    e = next(x for x in items if x["codigo"] == "HUA-00001")
    # Respeta InspectorAsignado del CSV (sin override).
    assert e["inspector_asignado"] == "Miguel Guzmán Millones"
    assert e["capacidad"] == Decimal("20")
    fid = [x for x in items if x["site"] == "FID"]
    assert len(fid) == 79
    assert all(x["inspector_asignado"] == "Jerson Romero" for x in fid)


def test_mantenimientos():
    items, errores = _parsear("mantenimientos")
    assert errores == []
    assert len(items) == 841
    m = items[0]
    assert m["precinto"] == "CUMPLE"  # "OK" normalizado
    assert m["gabinete"] in ("CUMPLE", "NO_CUMPLE", "NA")
    # incumplio: los levantados (fecha_levantamiento) deben quedar en true.
    levantados = [x for x in items if x.get("fecha_levantamiento")]
    assert levantados and all(x["incumplio"] for x in levantados)
    # conforme sin pendientes -> incumplio false
    conforme = next(
        x for x in items if x["resultado"] == "Conforme" and not x["fecha_levantamiento"]
    )
    assert conforme["incumplio"] is False


def test_aprobaciones():
    items, errores = _parsear("aprobaciones")
    assert errores == []
    assert len(items) == 1
