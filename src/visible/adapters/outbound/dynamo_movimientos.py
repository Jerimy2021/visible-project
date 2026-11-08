"""Repositorio de movimientos en DynamoDB (PK=telefono, SK=fecha#uuid)."""

import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from visible.domain.movimiento import Movimiento


class DynamoRepositorioMovimientos:
    def __init__(self, tabla: str | None = None) -> None:
        self.tabla_nombre = tabla or os.environ["TABLA_MOVIMIENTOS"]

    def guardar(self, telefono: str, movimientos: list[Movimiento]) -> None:
        import boto3

        tabla = boto3.resource("dynamodb").Table(self.tabla_nombre)
        creado = datetime.now(UTC).isoformat()
        with tabla.batch_writer() as lote:
            for m in movimientos:
                lote.put_item(
                    Item={
                        "telefono": telefono,
                        "sk": f"{m.fecha.isoformat()}#{uuid.uuid4()}",
                        "fecha": m.fecha.isoformat(),
                        "monto": m.monto,
                        "concepto": m.concepto,
                        "tipo": m.tipo.value,
                        "confianza": Decimal(str(m.confianza)),
                        "creado_en": creado,
                    }
                )
