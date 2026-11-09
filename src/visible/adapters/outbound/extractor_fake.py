"""Extractor de prueba: datos fijos realistas de una tienda de Gamarra."""

from datetime import date
from decimal import Decimal

from visible.application.extractor import Contenido, Extraccion
from visible.domain.movimiento import Categoria, Movimiento


class FakeExtractor:
    """Devuelve una Extraccion fija, ignorando el contenido real."""

    def extraer(self, contenido: Contenido) -> Extraccion:
        hoy = date.today()
        mov = lambda m, c, cat, sub, conf, org="": Movimiento(  # noqa: E731
            hoy, Decimal(m), c, cat, sub, conf, org, False, "cuaderno"
        )
        movimientos = [
            mov("135.00", "3 blusas", Categoria.INGRESO, "venta_yape", 0.95, "yape"),
            mov("80.00", "1 pantalón jean", Categoria.INGRESO, "venta_efectivo", 0.90, "efectivo"),
            mov("60.00", "2 polos algodón", Categoria.INGRESO, "venta_efectivo", 0.88, "efectivo"),
            mov("120.00", "compra de tela", Categoria.GASTO_NEGOCIO, "mercaderia", 0.85),
            mov("15.00", "menú del almuerzo", Categoria.GASTO_PERSONAL, "alimentacion", 0.80),
        ]
        return Extraccion(movimientos=movimientos, legible=True, tipo_entrada="cuaderno")
