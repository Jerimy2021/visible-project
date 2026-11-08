"""Repositorio de movimientos en DynamoDB (PK=telefono, SK=fecha#uuid)."""

import os
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from visible.domain.movimiento import Movimiento, TipoMovimiento


def _item_a_movimiento(item: dict) -> Movimiento:
    return Movimiento(
        fecha=date.fromisoformat(item["fecha"]),
        monto=Decimal(str(item["monto"])),
        concepto=item.get("concepto", ""),
        tipo=TipoMovimiento(item["tipo"]),
        confianza=float(item.get("confianza", 0)),
        origen=item.get("origen", ""),
    )


class DynamoRepositorioMovimientos:
    def __init__(self, tabla: str | None = None) -> None:
        self.tabla_nombre = tabla or os.environ["TABLA_MOVIMIENTOS"]

    def _tabla(self):
        import boto3

        return boto3.resource("dynamodb").Table(self.tabla_nombre)

    def guardar(
        self, telefono: str, movimientos: list[Movimiento], evidencia_key: str = ""
    ) -> None:
        creado = datetime.now(UTC).isoformat()
        with self._tabla().batch_writer() as lote:
            for m in movimientos:
                item = {
                    "telefono": telefono,
                    "sk": f"{m.fecha.isoformat()}#{uuid.uuid4()}",
                    "fecha": m.fecha.isoformat(),
                    "monto": m.monto,
                    "concepto": m.concepto,
                    "tipo": m.tipo.value,
                    "confianza": Decimal(str(m.confianza)),
                    "origen": m.origen,
                    "creado_en": creado,
                }
                if evidencia_key:
                    item["evidencia_key"] = evidencia_key
                lote.put_item(Item=item)

    def leer_ventana(self, telefono: str, hoy: date, dias: int = 28) -> list[Movimiento]:
        """Movimientos de los últimos `dias` días (para el motor de puntaje)."""
        desde = (hoy - timedelta(days=dias - 1)).isoformat()
        from boto3.dynamodb.conditions import Key

        resp = self._tabla().query(
            KeyConditionExpression=Key("telefono").eq(telefono) & Key("sk").gte(desde)
        )
        return [_item_a_movimiento(i) for i in resp.get("Items", [])]

    def ultimos(self, telefono: str, limite: int = 20) -> list[dict]:
        """Últimos `limite` movimientos crudos (incluye evidencia_key) más recientes primero."""
        from boto3.dynamodb.conditions import Key

        resp = self._tabla().query(
            KeyConditionExpression=Key("telefono").eq(telefono),
            ScanIndexForward=False,
            Limit=limite,
        )
        return resp.get("Items", [])
