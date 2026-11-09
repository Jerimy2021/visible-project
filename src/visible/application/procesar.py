"""Caso de uso: procesar el contenido de un mensaje y responder al usuario.

Depende solo de puertos (Extractor, RepositorioMovimientos, Mensajero) y del
dominio. Sin AWS: testeable con dobles en memoria.
"""

from decimal import Decimal

from visible.application.extractor import Contenido, Extraccion, Extractor
from visible.application.mensajero import Mensajero
from visible.application.repositorio import RepositorioMovimientos
from visible.domain.movimiento import Categoria, Movimiento, categoria_desde_opcion

MENSAJE_SIN_DATOS = (
    "No pude leer movimientos en tu mensaje. ¿Me mandas una foto más clara "
    "del cuaderno, con buena luz y el texto completo? 🙏"
)
MENSAJE_ILEGIBLE = (
    "No pude leer bien la foto 😕. ¿Me la reenvías con buena luz, de frente y "
    "enfocando el texto del cuaderno?"
)
MAX_PREGUNTAS = 2


def _soles(monto: Decimal) -> str:
    return f"S/ {monto:.2f}"


def resumir(movimientos: list[Movimiento]) -> str:
    """Mensaje de confirmación con totales de ingresos y gastos."""
    ventas = [m for m in movimientos if m.categoria is Categoria.INGRESO]
    gastos = [
        m for m in movimientos if m.categoria in (Categoria.GASTO_NEGOCIO, Categoria.GASTO_PERSONAL)
    ]
    total_ventas = sum((m.monto for m in ventas), Decimal(0))
    total_gastos = sum((m.monto for m in gastos), Decimal(0))
    return (
        f"Registré {len(ventas)} ventas por {_soles(total_ventas)} y "
        f"{len(gastos)} gastos por {_soles(total_gastos)}. ¿Está bien?"
    )


def _preguntar(
    telefono: str,
    extraccion: Extraccion,
    sks: list[str],
    mensajero: Mensajero,
) -> None:
    """Envía hasta MAX_PREGUNTAS mensajes interactivos para desambiguar."""
    por_clasificar = [
        sk
        for m, sk in zip(extraccion.movimientos, sks, strict=False)
        if m.categoria is Categoria.POR_CLASIFICAR
    ]
    for i, pregunta in enumerate(extraccion.preguntas[:MAX_PREGUNTAS]):
        if i < len(por_clasificar):
            sk = por_clasificar[i]
        elif sks:
            sk = sks[0]
        else:
            continue
        opciones = [
            (f"clasif|{sk}|{categoria_desde_opcion(op)}", op[:20]) for op in pregunta.opciones[:10]
        ]
        mensajero.enviar_opciones(telefono, pregunta.pregunta, opciones)


def procesar(
    telefono: str,
    contenido: Contenido,
    extractor: Extractor,
    repositorio: RepositorioMovimientos,
    mensajero: Mensajero,
    evidencia_key: str = "",
) -> Extraccion:
    """Extrae, persiste y confirma. Devuelve la Extraccion."""
    extraccion = extractor.extraer(contenido)

    if not extraccion.legible:
        texto = extraccion.preguntas[0].pregunta if extraccion.preguntas else MENSAJE_ILEGIBLE
        mensajero.enviar_texto(telefono, texto)
        return extraccion

    if not extraccion.movimientos:
        mensajero.enviar_texto(telefono, MENSAJE_SIN_DATOS)
        return extraccion

    sks = repositorio.guardar(telefono, extraccion.movimientos, evidencia_key)
    mensajero.enviar_texto(telefono, resumir(extraccion.movimientos))
    _preguntar(telefono, extraccion, sks or [], mensajero)
    return extraccion
