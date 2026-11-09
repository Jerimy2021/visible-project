"""Guarda las evidencias (fotos del cuaderno) en S3."""

import os
from datetime import date

_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "application/pdf": "pdf",
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
}


def _extension(mime: str) -> str:
    # WhatsApp manda p. ej. "audio/ogg; codecs=opus": se ignoran los parámetros.
    return _EXT.get((mime or "").split(";")[0].strip(), "bin")


class S3Evidencias:
    def __init__(self, bucket: str | None = None) -> None:
        self.bucket = bucket or os.environ["BUCKET_EVIDENCIAS"]

    def guardar(self, telefono: str, media_id: str, datos: bytes, mime: str) -> str:
        """Sube el archivo y devuelve su key en S3."""
        import boto3

        key = f"evidencias/{telefono}/{date.today().isoformat()}/{media_id}.{_extension(mime)}"
        boto3.client("s3").put_object(Bucket=self.bucket, Key=key, Body=datos, ContentType=mime)
        return key

    def borrar_de(self, telefono: str) -> int:
        """Borra de verdad las evidencias y transcripciones de la usuaria.

        El bucket tiene versionado: se borran TODAS las versiones (y marcas de
        borrado); si no, los archivos seguirían recuperables. Devuelve cuántos
        archivos distintos había.
        """
        import boto3

        s3 = boto3.client("s3")
        archivos: set[str] = set()
        for prefijo in (f"evidencias/{telefono}/", f"transcripciones/{telefono}/"):
            for pagina in s3.get_paginator("list_object_versions").paginate(
                Bucket=self.bucket, Prefix=prefijo
            ):
                objetos = [
                    {"Key": v["Key"], "VersionId": v["VersionId"]}
                    for v in pagina.get("Versions", []) + pagina.get("DeleteMarkers", [])
                ]
                archivos.update(v["Key"] for v in pagina.get("Versions", []))
                for i in range(0, len(objetos), 1000):
                    s3.delete_objects(Bucket=self.bucket, Delete={"Objects": objetos[i : i + 1000]})
        return len(archivos)
