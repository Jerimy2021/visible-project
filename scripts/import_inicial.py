"""Carga inicial de las listas desde data/raw a DynamoDB (solo arranque del piloto).

El uso diario es por el servicio (POST /import/url + Lambda). Esto es para sembrar
las tablas la primera vez. Imprime el reporte por tabla y el conteo final.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import boto3  # noqa: E402

from visible.adapters.outbound.repositorio_import import upsert  # noqa: E402
from visible.domain.importacion import TABLAS, parsear  # noqa: E402
from visible.domain.usuarios import ROSTER_PILOTO, item_usuario  # noqa: E402

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
PREFIJO = "visible-"
LOGICOS = ["sites", "extintores", "mantenimientos", "aprobaciones"]


def main() -> None:
    print("Carga inicial Brigada → DynamoDB\n")
    for logico in LOGICOS:
        archivo = RAW / TABLAS[logico][0]
        items, errores = parsear(logico, archivo.read_bytes())
        preservar = ["incumplio"] if logico == "mantenimientos" else None
        rep = upsert(f"{PREFIJO}{logico}", items, TABLAS[logico][2], preservar)
        print(
            f"  {logico:<16} filas={len(items):>4}  nuevas={rep['nuevas']:>4}  "
            f"actualizadas={rep['actualizadas']:>4}  errores={len(errores) + len(rep['errores'])}"
        )
        for e in (errores + rep["errores"])[:5]:
            print(f"      ! {e}")

    usuarios = [item_usuario(u) for u in ROSTER_PILOTO]
    rep = upsert(f"{PREFIJO}usuarios", usuarios)
    print(
        f"  {'usuarios':<16} filas={len(usuarios):>4}  nuevas={rep['nuevas']:>4}  "
        f"actualizadas={rep['actualizadas']:>4}"
    )

    print("\nConteo por tabla:")
    dynamo = boto3.client("dynamodb")
    for logico in [*LOGICOS, "usuarios"]:
        tabla = f"{PREFIJO}{logico}"
        total = dynamo.scan(TableName=tabla, Select="COUNT")["Count"]
        print(f"  {tabla:<28} {total}")


if __name__ == "__main__":
    main()
