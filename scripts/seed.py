"""Carga 3 emprendedoras demo con 4 semanas de movimientos realistas.

Uso:
    python scripts/seed.py --dry-run   # solo calcula e imprime puntajes
    python scripts/seed.py             # escribe en DynamoDB (perfiles + movimientos)
"""

import argparse
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from visible.domain.movimiento import Movimiento, TipoMovimiento  # noqa: E402
from visible.domain.puntaje import evaluar  # noqa: E402

HOY = date.today()
TABLA_MOV = "visible-movimientos"
TABLA_PERF = "visible-perfiles"


def _dia(semana: int, offset: int) -> date:
    """Fecha dentro de la semana (0=más antigua..3=más reciente), offset 0..6."""
    dias_atras = (3 - semana) * 7 + (6 - offset)
    return HOY - timedelta(days=dias_atras)


def construir(cfg: dict) -> list[Movimiento]:
    """Genera movimientos a partir de totales por semana y días de registro."""
    movs: list[Movimiento] = []
    for semana, total in enumerate(cfg["ventas_sem"]):
        if total == 0:
            continue
        dias = cfg["dias_sem"][semana]
        monto = Decimal(total) / dias
        n_yape = round(dias * cfg["yape_ratio"])
        for d in range(dias):
            origen = "yape" if d < n_yape else "efectivo"
            movs.append(
                Movimiento(
                    _dia(semana, d), monto, "ventas del día", TipoMovimiento.VENTA, 0.9, origen
                )
            )
        # Gastos: sobre días ya con registro (no inflan la constancia)
        gasto_total = cfg["gastos_sem"][semana]
        if gasto_total:
            movs.append(
                Movimiento(
                    _dia(semana, 0),
                    Decimal(gasto_total),
                    "compra de mercadería",
                    TipoMovimiento.GASTO_NEGOCIO,
                    0.9,
                )
            )
    return movs


DEMO = [
    {
        "telefono": "51900000001",
        "nombre": "Carmen Quispe",
        "rubro": "Ropa",
        "zona": "Gamarra",
        "ventas_sem": [1000, 1250, 800, 1100],
        "gastos_sem": [640, 770, 540, 620],
        "dias_sem": [5, 6, 5, 5],
        "yape_ratio": 0.6,
    },
    {
        "telefono": "51900000002",
        "nombre": "Lucía Ramírez",
        "rubro": "Bodega",
        "zona": "SJL",
        "ventas_sem": [700, 500, 900, 720],
        "gastos_sem": [520, 380, 680, 535],
        "dias_sem": [5, 4, 5, 4],
        "yape_ratio": 0.5,
    },
    {
        "telefono": "51900000003",
        "nombre": "Marisol Torres",
        "rubro": "Comida",
        "zona": "Comas",
        "ventas_sem": [0, 0, 600, 700],
        "gastos_sem": [0, 0, 250, 280],
        "dias_sem": [0, 0, 5, 5],
        "yape_ratio": 0.5,
    },
]


def _borrar_movimientos(tabla, telefono: str) -> None:
    from boto3.dynamodb.conditions import Key

    items = tabla.query(KeyConditionExpression=Key("telefono").eq(telefono)).get("Items", [])
    with tabla.batch_writer() as lote:
        for it in items:
            lote.delete_item(Key={"telefono": telefono, "sk": it["sk"]})


def escribir(demo: list[dict], movimientos_por_persona: dict) -> None:
    import boto3

    from visible.adapters.outbound.dynamo_movimientos import DynamoRepositorioMovimientos

    dynamo = boto3.resource("dynamodb")
    t_mov = dynamo.Table(TABLA_MOV)
    t_perf = dynamo.Table(TABLA_PERF)
    repo = DynamoRepositorioMovimientos(TABLA_MOV)

    for cfg in demo:
        tel = cfg["telefono"]
        _borrar_movimientos(t_mov, tel)
        repo.guardar(tel, movimientos_por_persona[tel])
        t_perf.put_item(
            Item={
                "telefono": tel,
                "nombre": cfg["nombre"],
                "rubro": cfg["rubro"],
                "zona": cfg["zona"],
                "consentimiento": (HOY - timedelta(days=30)).isoformat(),
                "creado_en": (HOY - timedelta(days=30)).isoformat(),
            }
        )
        print(
            f"  escrito: {cfg['nombre']} ({tel}) — {len(movimientos_por_persona[tel])} movimientos"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="solo imprime puntajes")
    args = parser.parse_args()

    movimientos = {cfg["telefono"]: construir(cfg) for cfg in DEMO}

    print("Puntajes calculados:")
    for cfg in DEMO:
        ev = evaluar(movimientos[cfg["telefono"]], hoy=HOY)
        print(
            f"  {cfg['nombre']:<16} {cfg['rubro']:<7} {cfg['zona']:<8} "
            f"puntaje={str(ev.puntaje):>4} estado={ev.estado:<12} "
            f"tend={ev.tendencia_pct:>6}% estab={ev.estabilidad:<5} "
            f"const={ev.constancia} yape={ev.coincidencia_yape_pct} "
            f"monto={ev.decision.monto}"
        )

    if args.dry_run:
        print("\n(dry-run: no se escribió nada)")
        return

    print("\nEscribiendo en DynamoDB...")
    escribir(DEMO, movimientos)
    print("Listo.")


if __name__ == "__main__":
    main()
