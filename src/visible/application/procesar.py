"""Caso de uso: procesar el contenido de un mensaje y responder al usuario.

Depende solo de puertos (Extractor, RepositorioMovimientos, Mensajero) y del
dominio. Sin AWS: testeable con dobles en memoria.
"""

from datetime import date
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
MAX_LINEAS = 5

_DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
_ETIQUETA = {
    Categoria.INGRESO: "Venta",
    Categoria.GASTO_NEGOCIO: "Negocio",
    Categoria.GASTO_PERSONAL: "Personal",
    Categoria.DEUDA: "Deuda",
    Categoria.MOVIMIENTO_INTERNO: "Interno",
    Categoria.POR_CLASIFICAR: "¿?",
}


def soles_es(monto: Decimal) -> str:
    """Monto estilo peruano: "S/ 1 840" (espacio de miles; sin ,00 si es entero)."""
    n = Decimal(str(monto))
    if n == n.to_integral_value():
        cuerpo = f"{int(n):,}".replace(",", " ")
    else:
        cuerpo = f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", " ")
    return f"S/ {cuerpo}"


def _dia_es(fecha: date) -> str:
    return f"{_DIAS[fecha.weekday()]} {fecha.day}"


def resumir(movimientos: list[Movimiento]) -> str:
    """Confirmación "Esto leí (sáb 7):" con una línea por movimiento (máx 5) + total."""
    fecha = max((m.fecha for m in movimientos), default=date.today())
    lineas = []
    for m in movimientos[:MAX_LINEAS]:
        signo = "+" if m.categoria is Categoria.INGRESO else "−"
        lineas.append(f"{signo} {soles_es(m.monto)} · {m.concepto} · {_ETIQUETA[m.categoria]}")
    ingresos = sum((m.monto for m in movimientos if m.categoria is Categoria.INGRESO), Decimal(0))
    gastos = sum((m.monto for m in movimientos if m.categoria is not Categoria.INGRESO), Decimal(0))
    total = f"Total: + {soles_es(ingresos)} vendido · − {soles_es(gastos)} gastado"
    return f"Esto leí ({_dia_es(fecha)}):\n" + "\n".join(lineas) + "\n" + total


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
