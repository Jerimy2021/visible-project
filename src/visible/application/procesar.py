"""Caso de uso: procesar el contenido de un mensaje y responder al usuario.

Depende solo de puertos (Extractor, RepositorioMovimientos, Mensajero) y del
dominio. Sin AWS: testeable con dobles en memoria.
"""

from decimal import Decimal

from visible.application.extractor import Contenido, Extractor
from visible.application.mensajero import Mensajero
from visible.application.repositorio import RepositorioMovimientos
from visible.domain.movimiento import Movimiento

MENSAJE_SIN_DATOS = (
    "No pude leer movimientos en tu mensaje. ¿Me mandas una foto más clara "
    "del cuaderno, con buena luz y el texto completo? 🙏"
)


def _soles(monto: Decimal) -> str:
    return f"S/ {monto:.2f}"


def resumir(movimientos: list[Movimiento]) -> str:
    """Arma el mensaje de confirmación con totales de ventas y gastos."""
    ventas = [m for m in movimientos if m.es_venta]
    gastos = [m for m in movimientos if not m.es_venta]
    total_ventas = sum((m.monto for m in ventas), Decimal(0))
    total_gastos = sum((m.monto for m in gastos), Decimal(0))
    return (
        f"Registré {len(ventas)} ventas por {_soles(total_ventas)} y "
        f"{len(gastos)} gastos por {_soles(total_gastos)}. ¿Está bien?"
    )


def procesar(
    telefono: str,
    contenido: Contenido,
    extractor: Extractor,
    repositorio: RepositorioMovimientos,
    mensajero: Mensajero,
    evidencia_key: str = "",
) -> list[Movimiento]:
    """Extrae, persiste y confirma. Devuelve los movimientos extraídos."""
    movimientos = extractor.extraer(contenido)
    if not movimientos:
        mensajero.enviar_texto(telefono, MENSAJE_SIN_DATOS)
        return []
    repositorio.guardar(telefono, movimientos, evidencia_key)
    mensajero.enviar_texto(telefono, resumir(movimientos))
    return movimientos
