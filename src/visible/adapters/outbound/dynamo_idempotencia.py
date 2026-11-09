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

    def registrar_lote(self, telefono: str, lote: str, sha: str) -> None:
        """Recuerda qué archivo generó un lote, para poder reenviarlo tras "Corregir"."""
        import boto3

        boto3.resource("dynamodb").Table(self.tabla_nombre).put_item(
            Item={
                "pk": f"lote#{telefono}#{lote}",
                "sha": sha,
                "ttl": int(time.time()) + 30 * 86400,
            }
        )

    def liberar_imagen_de_lote(self, telefono: str, lote: str) -> None:
        """Olvida el archivo de ese lote: si lo reenvía, ya no sale como duplicado."""
        import boto3

        tabla = boto3.resource("dynamodb").Table(self.tabla_nombre)
        item = tabla.get_item(Key={"pk": f"lote#{telefono}#{lote}"}).get("Item")
        if item and item.get("sha"):
            tabla.delete_item(Key={"pk": f"img#{telefono}#{item['sha']}"})
            tabla.delete_item(Key={"pk": f"lote#{telefono}#{lote}"})

    def borrar_imagenes(self, telefono: str) -> int:
        """Borra las huellas de fotos/audios y lotes de la usuaria ("borrar mis datos")."""
        import boto3
        from boto3.dynamodb.conditions import Attr

        tabla = boto3.resource("dynamodb").Table(self.tabla_nombre)
        filtro = Attr("pk").begins_with(f"img#{telefono}#") | Attr("pk").begins_with(
            f"lote#{telefono}#"
        )
        claves, kwargs = [], {"FilterExpression": filtro, "ProjectionExpression": "pk"}
        while True:
            resp = tabla.scan(**kwargs)
            claves += [it["pk"] for it in resp.get("Items", [])]
            if "LastEvaluatedKey" not in resp:
                break
            kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
        with tabla.batch_writer() as lote:
            for pk in claves:
                lote.delete_item(Key={"pk": pk})
        return len(claves)

    def liberar(self, mensaje_id: str) -> None:
        """Borra la reserva para que un reintento async pueda reprocesar."""
        import boto3

        boto3.resource("dynamodb").Table(self.tabla_nombre).delete_item(
            Key={"pk": f"msg#{mensaje_id}"}
        )
