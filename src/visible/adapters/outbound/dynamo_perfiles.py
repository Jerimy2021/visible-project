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
        """Alta del perfil al primer mensaje. El consentimiento arranca pendiente."""
        from botocore.exceptions import ClientError

        try:
            self._tabla().put_item(
                Item={
                    "telefono": telefono,
                    "nombre": nombre,
                    "rubro": "",
                    "zona": "",
                    "consentimiento": "",
                    "consentimiento_estado": "pendiente",
                    "creado_en": date.today().isoformat(),
                    "conceptos": {},
                },
                ConditionExpression="attribute_not_exists(telefono)",
            )
        except ClientError as e:
            if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise

    def estado_consentimiento(self, telefono: str) -> str:
        """pendiente | aceptado | rechazado. Compat: una fecha previa cuenta como aceptado."""
        item = self.obtener(telefono) or {}
        estado = item.get("consentimiento_estado")
        if estado:
            return estado
        return "aceptado" if item.get("consentimiento") else "pendiente"

    def aceptar_consentimiento(self, telefono: str) -> None:
        self._tabla().update_item(
            Key={"telefono": telefono},
            UpdateExpression="SET consentimiento_estado = :e, consentimiento = :f",
            ExpressionAttributeValues={":e": "aceptado", ":f": date.today().isoformat()},
        )

    def rechazar_consentimiento(self, telefono: str) -> None:
        self._tabla().update_item(
            Key={"telefono": telefono},
            UpdateExpression="SET consentimiento_estado = :e",
            ExpressionAttributeValues={":e": "rechazado"},
        )

    def esperar(self, telefono: str, que: str) -> None:
        """Marca qué respuesta esperamos de ella (p. ej. "alcanza" → un monto). '' = nada."""
        self._tabla().update_item(
            Key={"telefono": telefono},
            UpdateExpression="SET esperando = :e",
            ExpressionAttributeValues={":e": que},
        )

    def esperando(self, telefono: str) -> str:
        return (self.obtener(telefono) or {}).get("esperando", "")

    def borrar(self, telefono: str) -> None:
        """Elimina el perfil (consentimiento y conceptos aprendidos)."""
        self._tabla().delete_item(Key={"telefono": telefono})

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
