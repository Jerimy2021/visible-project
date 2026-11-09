"""Repositorio de perfiles en DynamoDB (PK=telefono)."""

import os
from datetime import date


class DynamoPerfiles:
    def __init__(self, tabla: str | None = None) -> None:
        self.tabla_nombre = tabla or os.environ["TABLA_PERFILES"]

    def _tabla(self):
        import boto3

        return boto3.resource("dynamodb").Table(self.tabla_nombre)

    def crear_si_no_existe(self, telefono: str, nombre: str = "") -> None:
        """Alta del perfil al primer mensaje; registra la fecha de consentimiento."""
        from botocore.exceptions import ClientError

        try:
            self._tabla().put_item(
                Item={
                    "telefono": telefono,
                    "nombre": nombre,
                    "rubro": "",
                    "zona": "",
                    "consentimiento": date.today().isoformat(),
                    "creado_en": date.today().isoformat(),
                    "conceptos": {},
                },
                ConditionExpression="attribute_not_exists(telefono)",
            )
        except ClientError as e:
            if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise

    def guardar(self, perfil: dict) -> None:
        self._tabla().put_item(Item=perfil)

    def obtener(self, telefono: str) -> dict | None:
        return self._tabla().get_item(Key={"telefono": telefono}).get("Item")

    def listar(self) -> list[dict]:
        return self._tabla().scan().get("Items", [])

    def conceptos(self, telefono: str) -> list[str]:
        """Conceptos aprendidos como "concepto = categoria" (para inyectar al prompt)."""
        item = self.obtener(telefono) or {}
        mapa = item.get("conceptos", {}) or {}
        return [f"{k} = {v}" for k, v in mapa.items()]

    def aprender(self, telefono: str, concepto: str, categoria: str) -> None:
        """Guarda concepto -> categoria para esta usuaria (read-modify-write del mapa)."""
        if not concepto:
            return
        item = self.obtener(telefono) or {"telefono": telefono}
        mapa = item.get("conceptos", {}) or {}
        mapa[concepto] = categoria
        self._tabla().update_item(
            Key={"telefono": telefono},
            UpdateExpression="SET conceptos = :m",
            ExpressionAttributeValues={":m": mapa},
        )
