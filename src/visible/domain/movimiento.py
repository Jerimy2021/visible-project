"""Modelo de dominio del movimiento financiero (sin dependencias de AWS)."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum

MAX_DIAS_ATRAS = 60


class Categoria(StrEnum):
    INGRESO = "ingreso"
    GASTO_NEGOCIO = "gasto_negocio"
    GASTO_PERSONAL = "gasto_personal"
    DEUDA = "deuda"
    POR_CLASIFICAR = "por_clasificar"
    MOVIMIENTO_INTERNO = "movimiento_interno"


# Compatibilidad con movimientos antiguos (campo `tipo`).
LEGACY_TIPO = {
    "venta": Categoria.INGRESO,
    "gasto_negocio": Categoria.GASTO_NEGOCIO,
    "gasto_casa": Categoria.GASTO_PERSONAL,
}


@dataclass(frozen=True)
class Movimiento:
    """Un movimiento con monto en soles. `confianza` en [0, 1]."""

    fecha: date
    monto: Decimal
    concepto: str
    categoria: Categoria
    subcategoria: str = ""
    confianza: float = 1.0
    origen: str = ""  # "yape" (captura), "yape_anotado" (declarado) o "efectivo"
    por_cobrar: bool = False
    tipo_entrada: str = ""  # cuaderno | yape | texto

    @property
    def es_ingreso(self) -> bool:
        return self.categoria is Categoria.INGRESO


def normalizar_fecha(fecha: date, recepcion: date, max_dias: int = MAX_DIAS_ATRAS) -> date:
    """Nunca futura ni > max_dias atrás; fuera de rango -> fecha de recepción."""
    if fecha > recepcion or fecha < recepcion - timedelta(days=max_dias):
        return recepcion
    return fecha


def categoria_desde_opcion(opcion: str) -> Categoria:
    """Mapea la etiqueta de un botón de desambiguación a una categoría."""
    o = opcion.lower()
    if "negocio" in o:
        return Categoria.GASTO_NEGOCIO
    if any(x in o for x in ("personal", "casa", "familia", "hogar")):
        return Categoria.GASTO_PERSONAL
    if any(x in o for x in ("venta", "ingreso", "cliente", "cobro")):
        return Categoria.INGRESO
    if any(x in o for x in ("deuda", "préstamo", "prestamo", "cuota")):
        return Categoria.DEUDA
    return Categoria.POR_CLASIFICAR
