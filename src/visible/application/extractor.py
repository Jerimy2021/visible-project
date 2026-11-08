"""Puerto de entrada de datos: extraer movimientos de una foto o texto."""

from dataclasses import dataclass
from typing import Protocol

from visible.domain.movimiento import Movimiento


@dataclass(frozen=True)
class Contenido:
    """Lo que se le entrega al extractor: texto y/o imagen."""

    texto: str = ""
    imagen: bytes | None = None
    mime_type: str = ""


class Extractor(Protocol):
    """Convierte contenido (foto del cuaderno / texto) en movimientos."""

    def extraer(self, contenido: Contenido) -> list[Movimiento]: ...
