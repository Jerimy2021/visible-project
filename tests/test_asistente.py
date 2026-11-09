"""Conversaciones completas del asistente con dobles en memoria (sin AWS ni Meta)."""

from datetime import timedelta
from decimal import Decimal

import pytest

from visible.adapters.inbound import procesar as bot
from visible.adapters.outbound.transcriptor import texto_de_resultado
from visible.application import intenciones as it
from visible.application.procesar import opciones_categoria, opciones_subcategoria, soles_es
from visible.domain.categorias import SUBCATEGORIAS
from visible.domain.movimiento import Categoria, Movimiento
from visible.domain.puntaje import hoy_lima

TEL = "51987654321"


# --- Dobles ---------------------------------------------------------------
class Mundo:
    def __init__(self):
        self.enviados: list[tuple] = []
        self.perfiles: dict[str, dict] = {}
        self.movs: dict[str, dict] = {}  # sk -> item
        self.idem: dict[str, dict] = {}
        self.s3: dict[str, bytes] = {}
        self.transcripcion = "vendí 3 polos a 25"
        self.n = 0

    def textos(self):
        return [e[2] for e in self.enviados]


@pytest.fixture
def mundo(monkeypatch):
    m = Mundo()

    class Sender:
        def enviar_texto(self, t, x):
            m.enviados.append(("texto", t, x, None))

        def enviar_opciones(self, t, x, ops):
            m.enviados.append(("opciones", t, x, ops))

        def enviar_link(self, t, x, etiqueta, url):
            m.enviados.append(("link", t, x, url))

    class Perfiles:
        def crear_si_no_existe(self, t, nombre=""):
            m.perfiles.setdefault(
                t,
                {
                    "telefono": t,
                    "consentimiento_estado": "pendiente",
                    "consentimiento": "",
                    "conceptos": {},
                },
            )

        def estado_consentimiento(self, t):
            return m.perfiles.get(t, {}).get("consentimiento_estado", "pendiente")

        def aceptar_consentimiento(self, t):
            m.perfiles[t].update(consentimiento_estado="aceptado", consentimiento="2026-11-09")

        def rechazar_consentimiento(self, t):
            m.perfiles[t]["consentimiento_estado"] = "rechazado"

        def obtener(self, t):
            return m.perfiles.get(t)

        def conceptos(self, t):
            return [f"{k} = {v}" for k, v in m.perfiles[t]["conceptos"].items()]

        def aprender(self, t, concepto, cat):
            m.perfiles[t]["conceptos"][concepto] = cat

        def esperar(self, t, que):
            m.perfiles[t]["esperando"] = que

        def esperando(self, t):
            return m.perfiles.get(t, {}).get("esperando", "")

        def borrar(self, t):
            m.perfiles.pop(t, None)

    class Repo:
        def guardar(self, t, movimientos, evidencia_key="", lote=""):
            sks = []
            for mv in movimientos:
                m.n += 1
                sk = f"{mv.fecha.isoformat()}#{m.n}"
                m.movs[sk] = {
                    "telefono": t,
                    "sk": sk,
                    "mov": mv,
                    "lote": lote,
                    "concepto": mv.concepto,
                    "categoria": mv.categoria.value,
                    "subcategoria": mv.subcategoria,
                }
                sks.append(sk)
            return sks

        def actualizar_categoria(self, t, sk, cat, sub=None):
            it_ = m.movs.get(sk)
            if not it_:
                return None
            it_["categoria"] = cat
            if sub is not None:
                it_["subcategoria"] = sub
            return it_["concepto"]

        def leer_ventana(self, t, hoy, dias=28):
            return [
                Movimiento(
                    v["mov"].fecha,
                    v["mov"].monto,
                    v["concepto"],
                    Categoria(v["categoria"]),
                    subcategoria=v["subcategoria"],
                )
                for v in m.movs.values()
                if v["telefono"] == t
            ]

        def borrar_lote(self, t, lote):
            sks = [k for k, v in m.movs.items() if v["telefono"] == t and v["lote"] == lote]
            for k in sks:
                del m.movs[k]
            return len(sks)

        def borrar_todo(self, t):
            sks = [k for k, v in m.movs.items() if v["telefono"] == t]
            for k in sks:
                del m.movs[k]
            return len(sks)

        def contar(self, t):
            fechas = [v["mov"].fecha.isoformat() for v in m.movs.values() if v["telefono"] == t]
            return len(fechas), min(fechas, default="")

    class Idem:
        def reservar(self, mid):
            if f"msg#{mid}" in m.idem:
                return False
            m.idem[f"msg#{mid}"] = {}
            return True

        def liberar(self, mid):
            m.idem.pop(f"msg#{mid}", None)

        def registrar_imagen(self, t, sha, fecha):
            k = f"img#{t}#{sha}"
            if k in m.idem:
                return m.idem[k]["fecha"]
            m.idem[k] = {"fecha": fecha}
            return None

        def registrar_lote(self, t, lote, sha):
            m.idem[f"lote#{t}#{lote}"] = {"sha": sha}

        def liberar_imagen_de_lote(self, t, lote):
            it_ = m.idem.pop(f"lote#{t}#{lote}", None)
            if it_:
                m.idem.pop(f"img#{t}#{it_['sha']}", None)

        def borrar_imagenes(self, t):
            ks = [k for k in m.idem if k.startswith((f"img#{t}#", f"lote#{t}#"))]
            for k in ks:
                del m.idem[k]
            return len(ks)

    class S3:
        def guardar(self, t, media_id, datos, mime):
            k = f"evidencias/{t}/{media_id}"
            m.s3[k] = datos
            return k

        def borrar_de(self, t):
            ks = [k for k in m.s3 if k.startswith(f"evidencias/{t}/")]
            for k in ks:
                del m.s3[k]
            return len(ks)

    class Media:
        def descargar(self, media_id):
            return (
                (b"AUDIO-" + media_id.encode(), "audio/ogg; codecs=opus")
                if media_id.startswith("aud")
                else (b"IMG-" + media_id.encode(), "image/jpeg")
            )

    class Transcriptor:
        def transcribir(self, t, media_id, key):
            return m.transcripcion

    import visible.adapters.outbound.transcriptor as tr

    for nombre, clase in [
        ("WhatsAppSender", Sender),
        ("DynamoPerfiles", Perfiles),
        ("DynamoRepositorioMovimientos", Repo),
        ("DynamoIdempotencia", Idem),
        ("S3Evidencias", S3),
        ("MetaMediaDownloader", Media),
    ]:
        monkeypatch.setattr(bot, nombre, clase)
    monkeypatch.setattr(tr, "TranscribeTranscriptor", Transcriptor)
    monkeypatch.setenv("EXTRACTOR", "fake")
    monkeypatch.setenv("TRANSCRIBIR", "on")
    monkeypatch.setenv("LINK_PANEL", "https://panel.test")
    return m


def _msg(m, texto="", medio=None):
    m.n += 1
    ev = {"telefono": TEL, "texto": texto, "mensaje_id": f"wamid.{m.n}", "medios": []}
    if medio:
        ev["medios"] = [[medio, "audio/ogg" if medio.startswith("aud") else "image/jpeg"]]
    return bot.handler(ev, None)


def _boton(m, id_):
    m.n += 1
    return bot.handler({"telefono": TEL, "clasificacion": id_, "mensaje_id": f"wamid.{m.n}"}, None)


def _aceptar(m):
    _msg(m, "hola")
    return _boton(m, "consent|aceptar")


# --- Consentimiento y menú ----------------------------------------------------
def test_consentimiento_leer_mas_y_aceptar(mundo):
    assert _msg(mundo, "hola")["estado"] == "consentimiento_pendiente"
    ids = [o[0] for o in mundo.enviados[-1][3]]
    assert ids == ["consent|aceptar", "consent|rechazar", "consent|leer"]
    _boton(mundo, "consent|leer")
    assert "Más detalle" in mundo.textos()[-2]
    assert _boton(mundo, "consent|aceptar")["estado"] == "consentimiento_aceptado"
    assert mundo.enviados[-1][3] == bot.OPCIONES_MENU  # menú tras aceptar


def test_sin_consentimiento_no_guarda_nada(mundo):
    _msg(mundo, "vendí 3 polos a 25")
    assert mundo.movs == {}
    assert _boton(mundo, "menu|resumen")["estado"] == "consentimiento_pendiente"


def test_menu_y_reacciones(mundo):
    _aceptar(mundo)
    assert _msg(mundo, "Hola!")["estado"] == "menu"
    assert _msg(mundo, "")["estado"] == "ignorado"  # una reacción no dispara nada
    assert _boton(mundo, "menu|registrar")["estado"] == "menu_registrar"
    assert "captura de Yape" in mundo.textos()[-1]


# --- Registrar, confirmar y corregir -----------------------------------------
def test_foto_confirmar_y_corregir_permite_reenviar(mundo):
    _aceptar(mundo)
    assert _msg(mundo, medio="img1")["estado"] == "ok"
    conf = [e for e in mundo.enviados if e[0] == "opciones" and e[2].startswith("Esto leí")][-1]
    ok_id, fix_id = [o[0] for o in conf[3]]
    assert ok_id.startswith("conf|ok|") and fix_id.startswith("conf|fix|")
    n = len(mundo.movs)
    assert n > 0
    assert _boton(mundo, ok_id)["estado"] == "confirmado"
    assert _boton(mundo, fix_id)["borrados"] == n
    assert mundo.movs == {}
    # Tras corregir, la misma foto ya no sale como duplicada.
    assert _msg(mundo, medio="img1")["estado"] == "ok"
    # Pero mandarla otra vez sin corregir, sí.
    assert _msg(mundo, medio="img1")["estado"] == "duplicado_imagen"


def test_clasificar_en_dos_pasos_y_aprende(mundo):
    _aceptar(mundo)
    _msg(mundo, "pasaje 6")
    sk = next(iter(mundo.movs))
    assert _boton(mundo, f"clasif|{sk}|gasto_negocio")["estado"] == "clasif_paso1"
    tipos = [o[0] for o in mundo.enviados[-1][3]]
    assert f"sub|{sk}|gasto_negocio|transporte_delivery" in tipos
    assert _boton(mundo, f"sub|{sk}|gasto_negocio|transporte_delivery")["estado"] == "clasificado"
    assert mundo.movs[sk]["subcategoria"] == "transporte_delivery"
    concepto = mundo.movs[sk]["concepto"]
    assert mundo.perfiles[TEL]["conceptos"][concepto] == "gasto_negocio (transporte_delivery)"


def test_clasificar_registro_borrado_no_crea_nada(mundo):
    _aceptar(mundo)
    assert _boton(mundo, "clasif|2026-11-01#999|gasto_personal")["estado"] == "clasif_inexistente"
    assert _boton(mundo, "sub|x|gasto_personal|nope")["estado"] == "ignorado"
    assert mundo.movs == {}


# --- Audios -----------------------------------------------------------------
def test_audio_se_transcribe_y_registra(mundo):
    _aceptar(mundo)
    assert _msg(mundo, medio="aud1")["estado"] == "ok"
    textos = mundo.textos()
    assert any(t.startswith("🎧 Recibí tu audio") for t in textos)
    assert any("Escuché: «vendí 3 polos a 25»" in t for t in textos)


def test_audio_con_pregunta_responde_la_intencion(mundo):
    _aceptar(mundo)
    mundo.transcripcion = "resumen de mi semana"
    assert _msg(mundo, medio="aud2")["estado"] in ("resumen", "resumen_vacio")
    assert mundo.movs == {}


def test_audio_sin_texto_pide_escribir_y_permite_reenviar(mundo):
    _aceptar(mundo)
    mundo.transcripcion = ""
    assert _msg(mundo, medio="aud3")["estado"] == "audio_sin_texto"
    mundo.transcripcion = "vendí 2 casacas a 80"
    assert _msg(mundo, medio="aud3")["estado"] == "ok"


def test_audio_desactivado(mundo, monkeypatch):
    _aceptar(mundo)
    monkeypatch.setenv("TRANSCRIBIR", "off")
    assert _msg(mundo, medio="aud4")["estado"] == "audio"
    assert mundo.textos()[-1] == bot.MENSAJE_AUDIO


def test_documento_no_soportado(mundo):
    _aceptar(mundo)
    mundo.n += 1
    r = bot.handler(
        {
            "telefono": TEL,
            "texto": "",
            "mensaje_id": "w.doc",
            "medios": [["doc1", "application/pdf"]],
        },
        None,
    )
    assert r["estado"] == "formato_no_soportado"


# --- ¿Me alcanza?, mis datos, borrar ---------------------------------------
def _sembrar(mundo, ventas, gastos):
    hoy = hoy_lima()
    bot.DynamoRepositorioMovimientos().guardar(
        TEL,
        [
            Movimiento(hoy - timedelta(days=1), Decimal(ventas), "ventas", Categoria.INGRESO),
            Movimiento(hoy - timedelta(days=2), Decimal(gastos), "tela", Categoria.GASTO_NEGOCIO),
        ],
    )


def test_me_alcanza_con_monto_y_en_dos_pasos(mundo):
    _aceptar(mundo)
    _sembrar(mundo, "1000", "400")  # ahorro 600
    assert _msg(mundo, "¿me alcanza para 500?")["estado"] == "alcanza"
    assert mundo.textos()[-1].startswith("Sí te alcanza")
    assert _boton(mundo, "menu|alcanza")["estado"] == "alcanza_pregunta"
    assert _msg(mundo, "S/ 800")["estado"] == "alcanza"
    assert "te faltan S/ 200" in mundo.textos()[-1]
    # Ya no espera: un monto suelto vuelve a ser un registro.
    assert _msg(mundo, "50")["estado"] == "ok"


def test_resumen_incluye_ahorro_y_link_de_ella(mundo):
    _aceptar(mundo)
    _sembrar(mundo, "1000", "400")
    assert _msg(mundo, "resumen")["estado"] == "resumen"
    tipo, _, texto, url = mundo.enviados[-1]
    assert tipo == "link" and "Tu ahorro S/ 600" in texto and "/?mi=" in url


def test_mis_datos_y_borrar_todo(mundo):
    _aceptar(mundo)
    _msg(mundo, medio="img9")
    assert _msg(mundo, "mis datos")["estado"] == "mis_datos"
    assert "registros" in mundo.enviados[-1][2]
    assert _msg(mundo, "quiero borrar mis datos")["estado"] == "borrar_pregunta"
    assert _boton(mundo, "borrar|no")["estado"] == "borrar_cancelado"
    assert mundo.movs
    r = _boton(mundo, "borrar|si")
    assert r["estado"] == "datos_borrados" and r["archivos"] == 1
    assert mundo.movs == {} and mundo.s3 == {} and TEL not in mundo.perfiles
    assert not [k for k in mundo.idem if k.startswith(("img#", "lote#"))]
    # Si vuelve a escribir, se le pide autorización otra vez.
    assert _msg(mundo, "hola")["estado"] == "consentimiento_pendiente"


# --- Piezas puras -----------------------------------------------------------
@pytest.mark.parametrize(
    "texto,nombre",
    [
        ("Hola", it.MENU),
        ("menú", it.MENU),
        ("buenas tardes", it.MENU),
        ("¿Cuánto gané?", it.RESUMEN),
        ("me alcanza para 300", it.ALCANZA),
        ("Mis datos", it.MIS_DATOS),
        ("borrar mis datos por favor", it.BORRAR),
        ("ver mi negocio", it.NEGOCIO),
        ("vendí 3 polos a 25", it.REGISTRO),
        ("hola, vendí 5 chompas a 40 y compré hilo 12", it.REGISTRO),
    ],
)
def test_detectar_intenciones(texto, nombre):
    assert it.detectar(texto).nombre == nombre


@pytest.mark.parametrize(
    "texto,monto",
    [
        ("me alcanza para 500", Decimal("500")),
        ("S/ 1 500", Decimal("1500")),
        ("1,500", Decimal("1500")),
        ("1500.50", Decimal("1500.50")),
        ("nada", None),
    ],
)
def test_extraer_monto(texto, monto):
    assert it.extraer_monto(texto) == monto


def test_limites_de_whatsapp_en_etiquetas():
    for subs in SUBCATEGORIAS.values():
        for _, etiqueta in subs:
            # ≤3 opciones van como botones (≤20); más, como lista (≤24).
            assert len(etiqueta) <= (20 if len(subs) <= 3 else 24), etiqueta
        assert len(subs) <= 10
    for _, etiqueta in bot.OPCIONES_MENU + bot.BOTONES_BORRAR:
        assert len(etiqueta) <= 24
    for _, etiqueta in bot.BOTONES_CONSENT:
        assert len(etiqueta) <= 20
    assert len(bot.AVISO_LEY_29733) <= 1024


def test_opciones_categoria_usa_las_de_la_ia_o_las_basicas():
    assert [o[1] for o in opciones_categoria("sk", ("Negocio", "Personal"))] == [
        "Negocio",
        "Personal",
    ]
    assert [o[1] for o in opciones_categoria("sk", ("Quién sabe",))] == [
        "Negocio",
        "Personal",
        "Deuda",
    ]
    assert opciones_subcategoria("sk", "por_clasificar") == []


def test_responder_alcanza_sin_ahorro():
    assert "todavía no tienes ahorro" in it.responder_alcanza(Decimal(100), Decimal(0), soles_es)


def test_texto_de_resultado_transcribe():
    datos = {"results": {"transcripts": [{"transcript": "vendí tres polos"}]}}
    assert texto_de_resultado(datos) == "vendí tres polos"
