"""Categorías y subcategorías con las etiquetas que ve la usuaria en WhatsApp.

Límites de WhatsApp: botones de respuesta ≤ 20 caracteres (máx. 3) y filas de
lista ≤ 24 caracteres (máx. 10). Las etiquetas de aquí ya los respetan.
"""

from visible.domain.movimiento import Categoria

# Subcategorías por categoría: (id, etiqueta para WhatsApp)
SUBCATEGORIAS: dict[Categoria, list[tuple[str, str]]] = {
    Categoria.INGRESO: [
        ("venta_efectivo", "Venta en efectivo"),
        ("venta_yape", "Venta por Yape"),
    ],
    Categoria.GASTO_NEGOCIO: [
        ("mercaderia", "Mercadería / insumos"),
        ("alquiler_puesto", "Alquiler del puesto"),
        ("transporte_delivery", "Transporte o delivery"),
        ("otros_negocio", "Otro del negocio"),
    ],
    Categoria.GASTO_PERSONAL: [
        ("alimentacion", "Comida / mercado"),
        ("colegio", "Colegio"),
        ("vivienda_servicios", "Casa y servicios"),
        ("salud", "Salud"),
        ("otros_personales", "Otro personal"),
    ],
    Categoria.DEUDA: [
        ("cuota_pagada", "Pagué una cuota"),
        ("prestamo_recibido", "Me prestaron"),
    ],
}

# Primer paso de clasificación (3 botones como máximo).
BOTONES_CATEGORIA: list[tuple[Categoria, str]] = [
    (Categoria.GASTO_NEGOCIO, "Negocio"),
    (Categoria.GASTO_PERSONAL, "Personal"),
    (Categoria.DEUDA, "Deuda"),
]


def subcategorias(categoria: Categoria | str) -> list[tuple[str, str]]:
    try:
        return SUBCATEGORIAS.get(Categoria(categoria), [])
    except ValueError:
        return []


def es_subcategoria_valida(categoria: Categoria | str, sub: str) -> bool:
    return any(s == sub for s, _ in subcategorias(categoria))
