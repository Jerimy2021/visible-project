"""Puerto de salida: persistencia de movimientos."""

from typing import Protocol

from visible.domain.movimiento import Movimiento


class RepositorioMovimientos(Protocol):
    def guardar(
        self, telefono: str, movimientos: list[Movimiento], evidencia_key: str = ""
    ) -> None: ...
