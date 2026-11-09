"""Puerto de entrada de datos: extraer movimientos de una foto o texto."""

from dataclasses import dataclass, field
from typing import Protocol

from visible.domain.movimiento import Movimiento


@dataclass(frozen=True)
class Contenido:
    """Lo que se le entrega al extractor: texto y/o imagen + contexto de la usuaria."""

    texto: str = ""
    imagen: bytes | None = None
    mime_type: str = ""
    conceptos: tuple[str, ...] = ()  # conceptos aprendidos "concepto = categoria"


@dataclass(frozen=True)
class Pregunta:
    """Pregunta de desambiguación sobre un movimiento (de Flor)."""

    texto_original: str
    pregunta: str
    opciones: tuple[str, ...]


@dataclass(frozen=True)
class Extraccion:
    """Resultado del extractor: movimientos + metadatos (legible, preguntas, alertas)."""

    movimientos: list[Movimiento] = field(default_factory=list)
    legible: bool = True
    preguntas: list[Pregunta] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)
    tipo_entrada: str = ""  # cuaderno | yape | plin | texto


class Extractor(Protocol):
    """Convierte contenido (foto del cuaderno / texto) en una Extraccion."""

    def extraer(self, contenido: Contenido) -> Extraccion: ...
