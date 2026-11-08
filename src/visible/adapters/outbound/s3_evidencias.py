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
    return _EXT.get(mime, "bin")


class S3Evidencias:
    def __init__(self, bucket: str | None = None) -> None:
        self.bucket = bucket or os.environ["BUCKET_EVIDENCIAS"]

    def guardar(self, telefono: str, media_id: str, datos: bytes, mime: str) -> str:
        """Sube el archivo y devuelve su key en S3."""
        import boto3

        key = f"evidencias/{telefono}/{date.today().isoformat()}/{media_id}.{_extension(mime)}"
        boto3.client("s3").put_object(
            Bucket=self.bucket, Key=key, Body=datos, ContentType=mime
        )
        return key
