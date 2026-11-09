"""Transcripción de notas de voz con Amazon Transcribe (batch, español).

El audio ya está en S3 (evidencias). Se lanza un trabajo, se espera a que
termine (normalmente 10–30 s para una nota de voz corta) y se lee el texto.
"""

import contextlib
import json
import os
import re
import time

TIEMPO_MAX_S = 75  # la función procesar tiene Timeout 120 s


def _formato(key: str) -> str:
    ext = key.rsplit(".", 1)[-1].lower()
    return {
        "ogg": "ogg",
        "mp3": "mp3",
        "m4a": "mp4",
        "mp4": "mp4",
        "wav": "wav",
        "amr": "amr",
        "webm": "webm",
        "flac": "flac",
    }.get(ext, "ogg")


class TranscribeTranscriptor:
    def __init__(self, bucket: str | None = None, idioma: str | None = None) -> None:
        self.bucket = bucket or os.environ["BUCKET_EVIDENCIAS"]
        # es-US es el español latinoamericano de Transcribe.
        self.idioma = idioma or os.environ.get("TRANSCRIBE_IDIOMA", "es-US")

    def transcribir(self, telefono: str, media_id: str, key_audio: str) -> str:
        """Devuelve el texto de la nota de voz ('' si no se pudo)."""
        import boto3

        transcribe = boto3.client("transcribe")
        s3 = boto3.client("s3")
        nombre = re.sub(r"[^0-9A-Za-z._-]", "-", f"visible-{media_id}")[:200]
        salida = f"transcripciones/{telefono}/{nombre}.json"
        # Si ya existe (reintento del mismo audio), solo esperamos su resultado.
        with contextlib.suppress(transcribe.exceptions.ConflictException):
            transcribe.start_transcription_job(
                TranscriptionJobName=nombre,
                LanguageCode=self.idioma,
                MediaFormat=_formato(key_audio),
                Media={"MediaFileUri": f"s3://{self.bucket}/{key_audio}"},
                OutputBucketName=self.bucket,
                OutputKey=salida,
            )

        limite = time.monotonic() + TIEMPO_MAX_S
        while time.monotonic() < limite:
            job = transcribe.get_transcription_job(TranscriptionJobName=nombre)
            estado = job["TranscriptionJob"]["TranscriptionJobStatus"]
            if estado == "COMPLETED":
                datos = json.loads(s3.get_object(Bucket=self.bucket, Key=salida)["Body"].read())
                return texto_de_resultado(datos)
            if estado == "FAILED":
                return ""
            time.sleep(2)
        return ""


def texto_de_resultado(datos: dict) -> str:
    """Saca el texto del JSON de salida de Transcribe."""
    partes = datos.get("results", {}).get("transcripts", [])
    return " ".join(p.get("transcript", "") for p in partes).strip()
