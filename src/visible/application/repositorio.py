"""Puerto de salida: persistencia de movimientos."""

from typing import Protocol

from visible.domain.movimiento import Movimiento


class RepositorioMovimientos(Protocol):
    def guardar(
        self,
        telefono: str,
        movimientos: list[Movimiento],
        evidencia_key: str = "",
        lote: str = "",
    ) -> list[str]:
        """Persiste los movimientos y devuelve sus sk (alineados por índice).

        `lote` agrupa lo guardado de un mismo mensaje (para "Corregir")."""
        ...
