"""Parseo y normalización de los CSV a items de DynamoDB (uno por tabla).

Puro y testeable con los CSV reales. `Codigo` -> `codigo` (Title de SharePoint).
"""

import csv
import io

from visible.domain.fechas import normalizar_fecha
from visible.domain.normalizacion import booleano, numero, texto
from visible.domain.usuarios import INSPECTOR_PILOTO

PUNTOS = [
    ("precinto", "Precinto"),
    ("pasador", "Pasador"),
    ("presion", "Presion"),
    ("tarjeta", "Tarjeta"),
    ("libre_acceso", "LibreAcceso"),
    ("senaletica", "Senaletica"),
    ("gabinete", "Gabinete"),
    ("cilindro", "Cilindro"),
    ("manguera", "Manguera"),
]

# nombre lógico -> (archivo CSV, env de la tabla, claves)
TABLAS = {
    "sites": ("sites.csv", "TABLA_SITES", ["codigo"]),
    "extintores": ("Extintores.csv", "TABLA_EXTINTORES", ["codigo"]),
    "mantenimientos": (
        "MantenimientosMensuales.csv",
        "TABLA_MANTENIMIENTOS",
        ["codigo", "periodo"],
    ),
    "aprobaciones": ("AprobacionesMes.csv", "TABLA_APROBACIONES", ["site", "periodo"]),
}
_ARCHIVO_A_LOGICO = {
    "sites": "sites",
    "extintores": "extintores",
    "mantenimientosmensuales": "mantenimientos",
    "aprobacionesmes": "aprobaciones",
}


def tabla_de_archivo(nombre: str) -> str:
    base = nombre.lower().rsplit("/", 1)[-1].removesuffix(".csv")
    return _ARCHIVO_A_LOGICO.get(base, "")


# --- Mapeadores por tabla --------------------------------------------------


def _sites(f: dict) -> dict | None:
    codigo = texto(f.get("CodigoSite"))
    if not codigo:
        return None
    return {
        "codigo": codigo,
        "nombre": texto(f.get("NombreSite")),
        "empresa": texto(f.get("Empresa")),
        "pais": texto(f.get("Pais")),
        "supervisor_ssoma": texto(f.get("SupervisorSSOMA")),
        "correo_grupo": texto(f.get("CorreoGrupoSite")),
        "activo": bool(booleano(f.get("Activo"))),
    }


def _extintores(f: dict) -> dict | None:
    codigo = texto(f.get("Codigo"))
    if not codigo:
        return None
    item = {
        "codigo": codigo,
        "site": texto(f.get("Site")),
        "piso": texto(f.get("Piso")),
        "ubicacion": texto(f.get("UbicacionDetalle")),
        "zona_brigada": texto(f.get("ZonaBrigada")),
        "tipo": texto(f.get("Tipo")),
        "unidad_capacidad": texto(f.get("UnidadCapacidad")),
        "marca": texto(f.get("Marca")),
        "numero_serie": texto(f.get("NumeroSerie")),
        "fecha_fabricacion": normalizar_fecha(f.get("FechaFabricacion", "")),
        "fecha_fin_vida": normalizar_fecha(f.get("FechaFinVidaUtil", "")),
        "fecha_prox_insp_anual": normalizar_fecha(f.get("FechaProxInspAnual", "")),
        "fecha_ult_insp_anual": normalizar_fecha(f.get("FechaUltInspAnual", "")),
        "fecha_prox_ph": normalizar_fecha(f.get("FechaProxPH", "")),
        "ph_por_confirmar": bool(booleano(f.get("PH_PorConfirmar"))),
        "fecha_ult_mant_mensual": normalizar_fecha(f.get("FechaUltMantMensual", "")),
        "fecha_prox_mant_mensual": normalizar_fecha(f.get("FechaProxMantMensual", "")),
        "estado": texto(f.get("Estado")),
        # Piloto: todos los extintores se asignan al inspector del piloto.
        "inspector_asignado": INSPECTOR_PILOTO,
        "activo": bool(booleano(f.get("Activo"))),
    }
    for dynamo_col, csv_col in (("numero_original", "NumeroOriginal"), ("capacidad", "Capacidad")):
        n = numero(f.get(csv_col))
        if n is not None:
            item[dynamo_col] = n
    return item


def _mantenimientos(f: dict) -> dict | None:
    codigo = texto(f.get("Codigo"))
    periodo = texto(f.get("Periodo"))
    if not codigo or not periodo:
        return None
    item = {
        "codigo": codigo,
        "periodo": periodo,
        "site": texto(f.get("Site")),
        "fecha_inspeccion": normalizar_fecha(f.get("FechaInspeccion", "")),
        "tipo_ejecutor": texto(f.get("TipoEjecutor")),
        "inspector": texto(f.get("Inspector")),
        "cantidad_p": int(numero(f.get("CantidadP")) or 0),
        "resultado": texto(f.get("Resultado")),
        "observacion": texto(f.get("Observacion")),
        "fecha_levantamiento": normalizar_fecha(f.get("FechaLevantamiento", "")),
        "hoja_origen": texto(f.get("HojaOrigen")),
    }
    for dynamo_col, csv_col in PUNTOS:
        item[dynamo_col] = texto(f.get(csv_col))  # "OK" / "P" / "NA"
    return item


def _aprobaciones(f: dict) -> dict | None:
    periodo = texto(f.get("Periodo"))
    site = texto(f.get("Site"))
    if not periodo or not site:
        return None
    item = {
        "site": site,
        "periodo": periodo,
        "aprobado_por": texto(f.get("AprobadoPor")),
        "fecha_aprobacion": normalizar_fecha(f.get("FechaAprobacion", "")),
        "comentario": texto(f.get("Comentario")),
        "estado": texto(f.get("Estado")),
    }
    n = numero(f.get("TotalInspeccionados"))
    if n is not None:
        item["total_inspeccionados"] = int(n)
    return item


_MAPEADORES = {
    "sites": _sites,
    "extintores": _extintores,
    "mantenimientos": _mantenimientos,
    "aprobaciones": _aprobaciones,
}


def parsear(logico: str, contenido: bytes) -> tuple[list[dict], list[str]]:
    """Devuelve (items, errores) para la tabla lógica dada."""
    mapear = _MAPEADORES.get(logico)
    if not mapear:
        return [], [f"tabla desconocida: {logico}"]
    lector = csv.DictReader(io.StringIO(contenido.decode("utf-8-sig")))
    items: list[dict] = []
    errores: list[str] = []
    for n, fila in enumerate(lector, start=2):
        try:
            item = mapear(fila)
            if item is None:
                errores.append(f"fila {n}: faltan claves obligatorias")
            else:
                items.append(item)
        except Exception as e:  # noqa: BLE001
            errores.append(f"fila {n}: {e}")
    return items, errores
