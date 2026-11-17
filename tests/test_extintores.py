from datetime import date

from visible.domain.extintores import ATRASADO, HECHO, POR_HACER, en_alcance, estado_inspeccion

HOY = date(2026, 11, 17)


def test_estado_inspeccion():
    e = {"activo": True, "site": "HUA", "fecha_prox_mant_mensual": "2026-11-15"}
    assert estado_inspeccion(e, [{"periodo": "2026-11"}], "2026-11", HOY) == HECHO
    assert estado_inspeccion(e, [], "2026-11", HOY) == ATRASADO  # venció el 15
    futuro = {"activo": True, "site": "HUA", "fecha_prox_mant_mensual": "2026-12-15"}
    assert estado_inspeccion(futuro, [], "2026-11", HOY) == POR_HACER


def test_en_alcance():
    assert en_alcance({"activo": True, "site": "HUA"}, "HUA")
    assert en_alcance({"activo": True, "site": "HUA"}, "Todas")
    assert not en_alcance({"activo": False, "site": "HUA"}, "HUA")
    assert not en_alcance({"activo": True, "site": "HUA"}, "LIM")
