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
