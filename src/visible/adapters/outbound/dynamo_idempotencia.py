"""Idempotencia de mensajes vía put condicional en DynamoDB (PK=pk)."""

import os
import time


class DynamoIdempotencia:
    def __init__(self, tabla: str | None = None, ttl_dias: int = 3) -> None:
        self.tabla_nombre = tabla or os.environ["TABLA_IDEMPOTENCIA"]
        self.ttl_dias = ttl_dias

    def reservar(self, mensaje_id: str) -> bool:
        """True si es la primera vez que se ve el mensaje; False si ya se procesó."""
        import boto3
        from botocore.exceptions import ClientError

        tabla = boto3.resource("dynamodb").Table(self.tabla_nombre)
        try:
            tabla.put_item(
                Item={"pk": f"msg#{mensaje_id}", "ttl": int(time.time()) + self.ttl_dias * 86400},
                ConditionExpression="attribute_not_exists(pk)",
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise

    def registrar_imagen(self, telefono: str, sha: str, fecha_iso: str) -> str | None:
        """Antiduplicados por foto. None si es nueva (la registra); si ya existía,
        devuelve la fecha en que se registró. Sin TTL: persiste durante el piloto."""
        import boto3
        from botocore.exceptions import ClientError

        tabla = boto3.resource("dynamodb").Table(self.tabla_nombre)
        pk = f"img#{telefono}#{sha}"
        try:
            tabla.put_item(
                Item={"pk": pk, "fecha": fecha_iso},
                ConditionExpression="attribute_not_exists(pk)",
            )
            return None
        except ClientError as e:
            if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise
            item = tabla.get_item(Key={"pk": pk}).get("Item", {})
            return item.get("fecha", "")

    def liberar(self, mensaje_id: str) -> None:
        """Borra la reserva para que un reintento async pueda reprocesar."""
        import boto3

        boto3.resource("dynamodb").Table(self.tabla_nombre).delete_item(
            Key={"pk": f"msg#{mensaje_id}"}
        )
