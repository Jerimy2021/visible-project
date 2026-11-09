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
        tipo_entrada=item.get("tipo_entrada", ""),
    )


class DynamoRepositorioMovimientos:
    def __init__(self, tabla: str | None = None) -> None:
        self.tabla_nombre = tabla or os.environ["TABLA_MOVIMIENTOS"]

    def _tabla(self):
        import boto3

        return boto3.resource("dynamodb").Table(self.tabla_nombre)

    def guardar(
        self,
        telefono: str,
        movimientos: list[Movimiento],
        evidencia_key: str = "",
        lote: str = "",
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
                    "tipo_entrada": m.tipo_entrada,
                    "creado_en": creado,
                }
                if evidencia_key:
                    item["evidencia_key"] = evidencia_key
                if lote:
                    item["lote"] = lote
                lote.put_item(Item=item)
        return sks

    def actualizar_categoria(
        self, telefono: str, sk: str, categoria: str, subcategoria: str | None = None
    ) -> str | None:
        """Cambia la categoría (y opcionalmente la subcategoría) y devuelve el concepto.

        Devuelve None si el movimiento ya no existe (p. ej. lo borró con "Corregir"):
        así un botón viejo nunca crea un registro vacío.
        """
        from botocore.exceptions import ClientError

        expr, valores = "SET categoria = :c", {":c": categoria}
        if subcategoria is not None:
            expr += ", subcategoria = :s"
            valores[":s"] = subcategoria
        try:
            resp = self._tabla().update_item(
                Key={"telefono": telefono, "sk": sk},
                UpdateExpression=expr,
                ExpressionAttributeValues=valores,
                ConditionExpression="attribute_exists(sk)",
                ReturnValues="ALL_NEW",
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return None
            raise
        return resp.get("Attributes", {}).get("concepto", "")

    def _todos(self, telefono: str) -> list[dict]:
        from boto3.dynamodb.conditions import Key

        items, kwargs = [], {"KeyConditionExpression": Key("telefono").eq(telefono)}
        while True:
            resp = self._tabla().query(**kwargs)
            items += resp.get("Items", [])
            if "LastEvaluatedKey" not in resp:
                return items
            kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    def _borrar(self, items: list[dict]) -> int:
        with self._tabla().batch_writer() as lote:
            for it in items:
                lote.delete_item(Key={"telefono": it["telefono"], "sk": it["sk"]})
        return len(items)

    def borrar_lote(self, telefono: str, lote: str) -> int:
        """Borra lo guardado de un mismo mensaje ("Corregir"). Devuelve cuántos borró."""
        if not lote:
            return 0
        return self._borrar([it for it in self._todos(telefono) if it.get("lote") == lote])

    def borrar_todo(self, telefono: str) -> int:
        """Borra todos los movimientos de la usuaria ("borrar mis datos")."""
        return self._borrar(self._todos(telefono))

    def contar(self, telefono: str) -> tuple[int, str]:
        """(cantidad de movimientos, fecha del primero) para "mis datos"."""
        items = self._todos(telefono)
        primero = min((it.get("fecha", "") for it in items), default="")
        return len(items), primero

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
