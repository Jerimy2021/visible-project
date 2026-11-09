"""Repositorio de movimientos en DynamoDB (PK=telefono, SK=fecha#uuid)."""

import os
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from visible.domain.movimiento import LEGACY_TIPO, Categoria, Movimiento


def _item_a_movimiento(item: dict) -> Movimiento:
    cat = item.get("categoria")
    categoria = (
        Categoria(cat) if cat else LEGACY_TIPO.get(item.get("tipo", ""), Categoria.POR_CLASIFICAR)
    )
    return Movimiento(
        fecha=date.fromisoformat(item["fecha"]),
        monto=Decimal(str(item["monto"])),
        concepto=item.get("concepto", ""),
        categoria=categoria,
        subcategoria=item.get("subcategoria", ""),
        confianza=float(item.get("confianza", 0)),
        origen=item.get("origen", ""),
        por_cobrar=bool(item.get("por_cobrar", False)),
    )


class DynamoRepositorioMovimientos:
    def __init__(self, tabla: str | None = None) -> None:
        self.tabla_nombre = tabla or os.environ["TABLA_MOVIMIENTOS"]

    def _tabla(self):
        import boto3

        return boto3.resource("dynamodb").Table(self.tabla_nombre)

    def guardar(
        self, telefono: str, movimientos: list[Movimiento], evidencia_key: str = ""
    ) -> list[str]:
        creado = datetime.now(UTC).isoformat()
        sks: list[str] = []
        with self._tabla().batch_writer() as lote:
            for m in movimientos:
                sk = f"{m.fecha.isoformat()}#{uuid.uuid4()}"
                sks.append(sk)
                item = {
                    "telefono": telefono,
                    "sk": sk,
                    "fecha": m.fecha.isoformat(),
                    "monto": m.monto,
                    "concepto": m.concepto,
                    "categoria": m.categoria.value,
                    "subcategoria": m.subcategoria,
                    "confianza": Decimal(str(m.confianza)),
                    "origen": m.origen,
                    "por_cobrar": m.por_cobrar,
                    "creado_en": creado,
                }
                if evidencia_key:
                    item["evidencia_key"] = evidencia_key
                lote.put_item(Item=item)
        return sks

    def actualizar_categoria(self, telefono: str, sk: str, categoria: str) -> str:
        """Cambia la categoría de un movimiento y devuelve su concepto."""
        resp = self._tabla().update_item(
            Key={"telefono": telefono, "sk": sk},
            UpdateExpression="SET categoria = :c",
            ExpressionAttributeValues={":c": categoria},
            ReturnValues="ALL_NEW",
        )
        return resp.get("Attributes", {}).get("concepto", "")

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
