"""Dominio Movimiento + caso de uso `procesar` con dobles en memoria."""

from datetime import date
from decimal import Decimal

from visible.adapters.outbound.extractor_fake import FakeExtractor
from visible.application.extractor import Contenido, Extraccion, Pregunta
from visible.application.procesar import MENSAJE_SIN_DATOS, procesar, resumir, soles_es
from visible.domain.movimiento import Categoria, Movimiento


class RepoMemoria:
    def __init__(self):
        self.guardados: list[tuple[str, list[Movimiento]]] = []

    def guardar(self, telefono, movimientos, evidencia_key="", lote=""):
        self.guardados.append((telefono, movimientos))
        self.lote = lote
        return [f"{m.fecha.isoformat()}#{i}" for i, m in enumerate(movimientos)]


class MensajeroMemoria:
    def __init__(self):
        self.enviados: list[tuple[str, str]] = []
        self.opciones: list[tuple[str, str, list]] = []

    def enviar_texto(self, telefono, texto):
        self.enviados.append((telefono, texto))

    def enviar_opciones(self, telefono, texto, opciones):
        self.opciones.append((telefono, texto, opciones))


class ExtractorFijo:
    def __init__(self, extraccion: Extraccion):
        self.extraccion = extraccion

    def extraer(self, contenido):
        return self.extraccion


def test_movimiento_es_ingreso():
    m = Movimiento(date.today(), Decimal("10"), "x", Categoria.INGRESO, confianza=0.9)
    g = Movimiento(date.today(), Decimal("10"), "x", Categoria.GASTO_PERSONAL, confianza=0.9)
    assert m.es_ingreso and not g.es_ingreso


def test_procesar_guarda_y_confirma():
    repo, mensajero = RepoMemoria(), MensajeroMemoria()
    ext = procesar("51999", Contenido(texto="x"), FakeExtractor(), repo, mensajero)
    assert len(ext.movimientos) == 5
    assert repo.guardados == [("51999", ext.movimientos)]
    # El resumen va con botones para confirmar o corregir el lote guardado.
    tel, texto, opciones = mensajero.opciones[0]
    assert tel == "51999" and texto.startswith("Esto leí")
    assert [o[0] for o in opciones] == [f"conf|ok|{repo.lote}", f"conf|fix|{repo.lote}"]


def test_procesar_sin_datos_no_guarda():
    repo, mensajero = RepoMemoria(), MensajeroMemoria()
    ext = procesar(
        "51999", Contenido(texto="borroso"), ExtractorFijo(Extraccion()), repo, mensajero
    )
    assert ext.movimientos == []
    assert repo.guardados == []
    assert mensajero.enviados == [("51999", MENSAJE_SIN_DATOS)]


def test_procesar_ilegible_pide_otra_foto():
    repo, mensajero = RepoMemoria(), MensajeroMemoria()
    extraccion = Extraccion(
        legible=False,
        preguntas=[Pregunta("", "No se ve. ¿Me mandas otra foto?", ())],
    )
    procesar("51999", Contenido(imagen=b"x"), ExtractorFijo(extraccion), repo, mensajero)
    assert repo.guardados == []
    assert "otra foto" in mensajero.enviados[0][1]


def test_procesar_envia_botones_por_clasificar():
    repo, mensajero = RepoMemoria(), MensajeroMemoria()
    movs = [
        Movimiento(date.today(), Decimal("6"), "pasaje", Categoria.POR_CLASIFICAR, confianza=0.5)
    ]
    extraccion = Extraccion(
        movimientos=movs,
        preguntas=[
            Pregunta("pasaje 6", "¿El pasaje fue del negocio o personal?", ("Negocio", "Personal"))
        ],
    )
    procesar("51999", Contenido(imagen=b"x"), ExtractorFijo(extraccion), repo, mensajero)
    assert len(mensajero.opciones) == 2  # resumen con confirmar + pregunta
    _, texto, opciones = mensajero.opciones[1]
    assert texto.startswith("¿El pasaje")
    ids = [o[0] for o in opciones]
    assert any(i.endswith("gasto_negocio") for i in ids)
    assert any(i.endswith("gasto_personal") for i in ids)


def test_soles_es():
    assert soles_es(Decimal("1840")) == "S/ 1 840"
    assert soles_es(Decimal("75")) == "S/ 75"
    assert soles_es(Decimal("75.50")) == "S/ 75,50"


def test_resumir_formato_esto_lei():
    movs = [
        Movimiento(date.today(), Decimal("75"), "3 polos", Categoria.INGRESO, confianza=0.9),
        Movimiento(date.today(), Decimal("30"), "hilo", Categoria.GASTO_NEGOCIO, confianza=0.9),
        Movimiento(date.today(), Decimal("20"), "menú", Categoria.GASTO_PERSONAL, confianza=0.9),
    ]
    texto = resumir(movs)
    assert texto.startswith("Esto leí (")
    assert "+ S/ 75 · 3 polos · Venta" in texto
    assert "− S/ 30 · hilo · Negocio" in texto
    assert "Total: + S/ 75 vendido · − S/ 50 gastado" in texto
