from datetime import date

from visible.domain.centro import centro, periodos_recientes
from visible.domain.usuarios import ROSTER_PILOTO

HOY = date(2026, 11, 17)


def _ext(cod):
    return {
        "codigo": cod,
        "site": "HUA",
        "activo": True,
        "inspector_asignado": "José Manuel Chanta Torres",
        "fecha_prox_mant_mensual": "2026-11-20",
    }


def _mant(cod, periodo, resultado, cantidad_p, inspector, **extra):
    base = {
        "codigo": cod,
        "site": "HUA",
        "periodo": periodo,
        "resultado": resultado,
        "cantidad_p": cantidad_p,
        "inspector": inspector,
    }
    base.update(extra)
    return base


DATOS = {
    "sites": [{"codigo": "HUA", "nombre": "CD Huachipa"}],
    "usuarios": ROSTER_PILOTO,
    "extintores": [_ext("HUA-1"), _ext("HUA-2"), _ext("HUA-3")],
    "aprobaciones": [{"site": "HUA", "periodo": "2026-11", "estado": "Pendiente"}],
    "mantenimientos": [
        _mant("HUA-1", "2026-11", "Conforme", 0, "Miguel Guzmán"),
        _mant(
            "HUA-2",
            "2026-11",
            "1 P (Presión)",
            1,
            "Miguel Guzmán Millones",
            presion="P",
            fecha_inspeccion="2026-11-05",
        ),
        _mant("HUA-2", "2026-10", "1 P", 1, "Miguel Guzmán", fecha_inspeccion="2026-10-05"),
        _mant(
            "HUA-1",
            "2026-09",
            "Conforme (levantado)",
            0,
            "Miguel Guzmán",
            fecha_inspeccion="2026-09-02",
            fecha_levantamiento="2026-09-06",
        ),
    ],
}


def test_periodos_recientes():
    assert periodos_recientes("2026-11", 6) == [
        "2026-06",
        "2026-07",
        "2026-08",
        "2026-09",
        "2026-10",
        "2026-11",
    ]


def test_centro_hua():
    c = centro("HUA", "2026-11", DATOS, hoy=HOY)
    assert c["total"] == 3
    assert c["inspeccionados"] == 2
    assert c["faltan"] == 1
    assert c["avance_pct"] == 67
    assert c["conformes_1a_pct"] == 50  # 1 de 2
    assert c["p_abiertos"] == 2  # HUA-2 en nov y oct, sin levantar
    assert c["tiempo_levantamiento_dias"] == 4  # HUA-1 sep: 02 -> 06
    assert c["inspectores_activos"] == 1  # las 3 grafías de Miguel = 1 usuario
    assert c["aprobacion"] == {"estado": "Pendiente"}


def test_centro_series():
    c = centro("HUA", "2026-11", DATOS, hoy=HOY)
    # Punto que más falla: Presión con 1
    assert c["punto_que_mas_falla"][0] == {"punto": "Presión", "p": 1}
    # Reincidente: HUA-2 con P en 2 meses
    assert {"codigo": "HUA-2", "meses": 2} in c["reincidentes"]
    # Por inspector: Miguel hizo 2, asignados 0; José Manuel asignados 3
    por = {f["inspector"]: f for f in c["por_inspector"]}
    assert por["Miguel Guzmán Millones"]["hechos"] == 2
    assert por["José Manuel Chanta Torres"]["asignados"] == 3
    # Alerta pendiente más antigua: HUA-2 de octubre
    assert c["alertas"]["pendientes"][0]["codigo"] == "HUA-2"
