"""Descarga de medios desde la Meta Cloud API (dos pasos: id -> url -> bytes)."""

import json
import os
import urllib.request

from visible.adapters.outbound import secrets


def _token() -> str:
    return secrets.leer(os.environ["META_ACCESS_TOKEN_PARAM"], descifrar=True)


class MetaMediaDownloader:
    def descargar(self, media_id: str) -> tuple[bytes, str]:
        """Devuelve (bytes, mime_type) del medio."""
        version = os.environ.get("GRAPH_API_VERSION", "v25.0")
        token = _token()
        cabeceras = {"Authorization": f"Bearer {token}"}

        meta_req = urllib.request.Request(
            f"https://graph.facebook.com/{version}/{media_id}", headers=cabeceras
        )
        with urllib.request.urlopen(meta_req, timeout=8) as r:  # noqa: S310
            meta = json.loads(r.read())

        archivo_req = urllib.request.Request(meta["url"], headers=cabeceras)
        with urllib.request.urlopen(archivo_req, timeout=20) as r:  # noqa: S310
            datos = r.read()
            mime = meta.get("mime_type") or r.headers.get("Content-Type", "")
        return datos, mime or "application/octet-stream"
