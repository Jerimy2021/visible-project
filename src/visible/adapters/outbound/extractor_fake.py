"""Extractor de prueba: datos fijos realistas de una tienda de Gamarra."""

from datetime import date
from decimal import Decimal

from visible.application.extractor import Contenido, Extraccion
from visible.domain.movimiento import Categoria, Movimiento


class FakeExtractor:
    """Devuelve una Extraccion fija, ignorando el contenido real."""

    def extraer(self, contenido: Contenido) -> Extraccion:
        hoy = date.today()
        movimientos = [
            Movimiento(
                hoy, Decimal("135.00"), "3 blusas", Categoria.INGRESO, "venta_yape", 0.95, "yape"
            ),
            Movimiento(
                hoy,
                Decimal("80.00"),
                "1 pantalón jean",
                Categoria.INGRESO,
                "venta_efectivo",
                0.90,
                "efectivo",
            ),
            Movimiento(
                hoy,
                Decimal("60.00"),
                "2 polos algodón",
                Categoria.INGRESO,
                "venta_efectivo",
                0.88,
                "efectivo",
            ),
            Movimiento(
                hoy,
                Decimal("120.00"),
                "compra de tela",
                Categoria.GASTO_NEGOCIO,
                "mercaderia",
                0.85,
            ),
            Movimiento(
                hoy,
                Decimal("15.00"),
                "menú del almuerzo",
                Categoria.GASTO_PERSONAL,
                "alimentacion",
                0.80,
            ),
        ]
        return Extraccion(movimientos=movimientos, legible=True)
