"""Modelo de dominio: un movimiento financiero extraído del cuaderno."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class TipoMovimiento(StrEnum):
    VENTA = "venta"
    GASTO_NEGOCIO = "gasto_negocio"
    GASTO_CASA = "gasto_casa"


@dataclass(frozen=True)
class Movimiento:
    """Un movimiento con monto en soles. `confianza` en [0, 1]."""

    fecha: date
    monto: Decimal
    concepto: str
    tipo: TipoMovimiento
    confianza: float

    @property
    def es_venta(self) -> bool:
        return self.tipo is TipoMovimiento.VENTA
