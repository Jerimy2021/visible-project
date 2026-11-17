"""Usuarios del piloto Brigada y unificación de alias de personas.

Un usuario = un `id` con varios `alias` (distintas grafías del nombre). Esto
evita el bug de la Power App donde "Miguel Guzmán", "Miguel Guzmán Millones" y
"Miguel Angel Guzman Millones" se contaban como 3 personas (0/47).
"""

from visible.domain.normalizacion import nombre_canonico

# Inspector al que se le asignan los extintores en el piloto.
INSPECTOR_PILOTO = "José Manuel Chanta Torres"

ROSTER_PILOTO = [
    {
        "id": "u-gponte",
        "nombre": "Gianella Ponte",
        "rol": "Administrador",
        "alias": ["Gianella Ponte", "Gianella Arcela Ponte Carrasco"],
        "telefono_whatsapp": "",
    },
    {
        "id": "u-jchanta",
        "nombre": INSPECTOR_PILOTO,
        "rol": "Inspector",
        "alias": [INSPECTOR_PILOTO, "Jose Manuel Chanta Torres"],
        "telefono_whatsapp": "",
    },
]


def item_usuario(usuario: dict) -> dict:
    """Item para DynamoDB. Omite telefono_whatsapp vacío (no entra al GSI)."""
    item = {
        "id": usuario["id"],
        "nombre": usuario["nombre"],
        "rol": usuario["rol"],
        "alias": list(usuario["alias"]),
    }
    if usuario.get("telefono_whatsapp"):
        item["telefono_whatsapp"] = usuario["telefono_whatsapp"]
    return item


def resolver_id(nombre: str, usuarios: list[dict]) -> str:
    """Devuelve el id del usuario cuyo alias coincide con `nombre` (sin tildes ni
    mayúsculas), o "" si ninguno coincide."""
    objetivo = nombre_canonico(nombre)
    if not objetivo:
        return ""
    for u in usuarios:
        if any(nombre_canonico(a) == objetivo for a in u.get("alias", [])):
            return u["id"]
    return ""
