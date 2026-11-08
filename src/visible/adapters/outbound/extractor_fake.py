"""Extractor de prueba: datos fijos realistas de una tienda de Gamarra.

Permite trabajar el flujo completo mientras Bedrock está bloqueado.
"""

from datetime import date
from decimal import Decimal

from visible.application.extractor import Contenido
from visible.domain.movimiento import Movimiento, TipoMovimiento


class FakeExtractor:
    """Devuelve movimientos fijos, ignorando el contenido real."""

    def extraer(self, contenido: Contenido) -> list[Movimiento]:
        hoy = date.today()
        return [
            Movimiento(hoy, Decimal("135.00"), "3 blusas", TipoMovimiento.VENTA, 0.95),
            Movimiento(hoy, Decimal("80.00"), "1 pantalón jean", TipoMovimiento.VENTA, 0.90),
            Movimiento(hoy, Decimal("60.00"), "2 polos algodón", TipoMovimiento.VENTA, 0.88),
            Movimiento(
                hoy, Decimal("120.00"), "compra de tela", TipoMovimiento.GASTO_NEGOCIO, 0.85
            ),
            Movimiento(hoy, Decimal("15.00"), "menú del almuerzo", TipoMovimiento.GASTO_CASA, 0.80),
        ]
