import { useEffect, useState } from "react";
import { getFicha } from "./api";
import { cuotaFrancesa, soles as solesExacto } from "./finance";
import type { Ficha, Movimiento, Totales } from "./types";

/* Vista de la emprendedora ("Mi negocio"). Se abre con /?mi=<id> desde el
   botón "Ver mi negocio" que manda el asistente de WhatsApp. Solo lectura. */

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const SUB: Record<string, string> = {
  venta_efectivo: "Ventas en efectivo",
  venta_yape: "Ventas por Yape",
  mercaderia: "Mercadería",
  alquiler_puesto: "Alquiler del puesto",
  transporte_delivery: "Transporte y delivery",
  otros_negocio: "Otros del negocio",
  alimentacion: "Alimentación",
  colegio: "Colegio",
  vivienda_servicios: "Casa y servicios",
  salud: "Salud",
  otros_personales: "Otros personales",
  cuota_pagada: "Cuotas pagadas",
  prestamo_recibido: "Préstamo recibido",
  otros: "Otros",
};
const CAT: Record<string, { l: string; cls: string; signo: string }> = {
  ingreso: { l: "Venta", cls: "in", signo: "+" },
  gasto_negocio: { l: "Negocio", cls: "neg", signo: "−" },
  gasto_personal: { l: "Personal", cls: "per", signo: "−" },
  deuda: { l: "Deuda", cls: "deu", signo: "−" },
  por_clasificar: { l: "Por clasificar", cls: "pc", signo: "" },
  movimiento_interno: { l: "Interno", cls: "pc", signo: "" },
};
const MIN_SEMANAS = 3;
// Para ella, montos redondeados (sin céntimos).
const soles = (n: number) => solesExacto(Math.round(n));
const cap = (t: string) => (t ? t[0].toUpperCase() + t.slice(1) : t);

const fechaCorta = (iso: string) => {
  const [, m, d] = (iso || "").split("-").map(Number);
  return m && d ? `${d} ${MESES[m - 1]}` : iso;
};
const rango = (desde: string, hasta: string) => {
  const [, m1, d1] = desde.split("-").map(Number);
  const [, m2, d2] = hasta.split("-").map(Number);
  return m1 === m2 ? `${d1}–${d2} ${MESES[m2 - 1]}` : `${d1} ${MESES[m1 - 1]} – ${d2} ${MESES[m2 - 1]}`;
};
const iniciales = (n: string) =>
  (n || "·").split(" ").slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "").join("") || "·";

type Tab = "inicio" | "tableros" | "credito";
type IrA = (t: Tab, seccion?: string) => void;

export default function Emprendedora({ id }: { id: string }) {
  const [ficha, setFicha] = useState<Ficha | null>(null);
  const [error, setError] = useState(false);
  const [tab, setTab] = useState<Tab>("inicio");
  const [seccion, setSeccion] = useState<string | null>(null);
  // Cambiar de pestaña siempre empieza arriba, o en la sección pedida (p. ej. "Gastos del negocio").
  const irA: IrA = (t, s) => { setTab(t); setSeccion(s ?? null); };
  useEffect(() => {
    if (seccion) document.getElementById(seccion)?.scrollIntoView({ behavior: "smooth", block: "start" });
    else window.scrollTo(0, 0);
  }, [tab, seccion]);

  // Auto-refresco cada 10 s: lo que manda por WhatsApp aparece solo.
  useEffect(() => {
    let activo = true;
    const cargar = () =>
      getFicha(id)
        .then((f) => activo && (setFicha(f), setError(false)))
        .catch(() => activo && setError(true));
    cargar();
    const t = setInterval(cargar, 10000);
    return () => { activo = false; clearInterval(t); };
  }, [id]);

  useEffect(() => {
    document.title = "Visible · Mi negocio";
  }, []);

  if (error && !ficha) {
    return (
      <div className="ella">
        <div className="ella-wrap">
          <div className="ella-card">No encontramos tu negocio. Vuelve a abrir el link que te mandó el asistente.</div>
        </div>
      </div>
    );
  }
  if (!ficha?.emprendedora) {
    return <div className="ella"><div className="ella-wrap"><div className="ella-card">Cargando…</div></div></div>;
  }

  return (
    <div className="ella">
      <div className="ella-wrap">
        <header className="ella-top">
          <div className="ella-ini">{iniciales(ficha.nombre)}</div>
          <div style={{ flex: 1 }}>
            <div className="ella-muted">Semana {rango(ficha.emprendedora.desde, ficha.emprendedora.hasta)}</div>
            <div className="ella-hola">Hola{ficha.nombre ? `, ${ficha.nombre.split(" ")[0]}` : ""}</div>
          </div>
          <span className="ella-sync">✓ Sincronizado</span>
        </header>

        {tab === "inicio" && <Inicio ficha={ficha} irA={irA} />}
        {tab === "tableros" && <Tableros ficha={ficha} />}
        {tab === "credito" && <Credito ficha={ficha} />}
      </div>

      <nav className="ella-nav">
        {([["inicio", "⌂", "Inicio"], ["tableros", "▥", "Tableros"], ["credito", "◎", "Mi crédito"]] as const).map(
          ([k, ic, l]) => (
            <button key={k} className={tab === k ? "on" : ""} onClick={() => irA(k)}>
              <span className="ic">{ic}</span>
              {l}
            </button>
          ),
        )}
      </nav>
    </div>
  );
}

/* ---------- Inicio ---------- */
function Inicio({ ficha, irA }: { ficha: Ficha; irA: IrA }) {
  const e = ficha.emprendedora!;
  const s = e.semana;
  const max = Math.max(1, ...e.por_dia.map((d) => Math.abs(d.ganancia)));
  const hoy = e.por_dia.length - 1;
  return (
    <>
      <section className="ella-hero">
        <div className="row-sb">
          <span className="ella-hero-l">Ganancia del negocio</span>
          {e.variacion_ganancia_pct != null && (
            <span className="ella-var">
              {e.variacion_ganancia_pct >= 0 ? "▲" : "▼"} {Math.abs(e.variacion_ganancia_pct).toFixed(0)}%
            </span>
          )}
        </div>
        <div className="ella-big">{soles(s.ganancia)}</div>
        <div className="ella-bars">
          {e.por_dia.map((d, i) => (
            <div key={d.fecha} className="ella-bar-col">
              <div
                className={`ella-bar ${i === hoy ? "hoy" : ""} ${d.ganancia < 0 ? "neg" : ""}`}
                style={{ height: `${Math.max(6, (Math.abs(d.ganancia) / max) * 56)}px` }}
                title={`${fechaCorta(d.fecha)}: ${soles(d.ganancia)}`}
              />
              <span className={i === hoy ? "b" : ""}>{d.letra}</span>
            </div>
          ))}
        </div>
        <div className="ella-ahorro">
          <span>Tu ahorro</span>
          <strong>{soles(s.ahorro)}</strong>
        </div>
      </section>

      <h3 className="ella-h">Mis tableros</h3>
      <div className="ella-tiles">
        <Tile ic="↑" cls="in" l="Ingresos" v={s.ventas} onClick={() => irA("tableros", "sec-ingreso")} />
        <Tile ic="▢" cls="neg" l="Gastos del negocio" v={s.gastos_negocio} onClick={() => irA("tableros", "sec-gasto_negocio")} />
        <Tile ic="⌂" cls="per" l="Gastos personales" v={s.gastos_personales} onClick={() => irA("tableros", "sec-gasto_personal")} />
        <Tile ic="⇄" cls="aho" l="Cuotas de deuda" v={s.cuotas_deuda} onClick={() => irA("tableros", "sec-deuda")} />
      </div>

      <section className="ella-card">
        <div className="row-sb">
          <h3 className="ella-h" style={{ margin: 0 }}>Últimos</h3>
          <span className="ella-muted">Registra por WhatsApp</span>
        </div>
        <ListaMovs movs={ficha.movimientos.slice(0, 3)} />
        <button className="ella-btn-soft" onClick={() => irA("tableros", "sec-registros")}>Ver todos</button>
      </section>

      <CaminoCredito ficha={ficha} onClick={() => irA("credito")} />

      {ficha.consentimiento && (
        <section className="ella-card ella-row">
          <span className="ella-tile-ic aho">✓</span>
          <div>
            <strong>Autorizaste el uso de tus datos</strong>
            <div className="ella-muted">desde {fechaCorta(ficha.consentimiento.slice(0, 10))} · Ley 29733</div>
          </div>
        </section>
      )}
    </>
  );
}

function Tile({ ic, cls, l, v, onClick }: { ic: string; cls: string; l: string; v: number; onClick: () => void }) {
  return (
    <button className="ella-tile" onClick={onClick}>
      <span className={`ella-tile-ic ${cls}`}>{ic}</span>
      <span className="ella-muted">{l}</span>
      <strong>{soles(v)}</strong>
    </button>
  );
}

function ListaMovs({ movs }: { movs: Movimiento[] }) {
  if (!movs.length) {
    return <p className="ella-muted">Aún no hay registros. Mándale al asistente una foto de tu cuaderno.</p>;
  }
  return (
    <ul className="ella-movs">
      {movs.map((m, i) => {
        const c = CAT[m.categoria] ?? CAT.por_clasificar;
        const fuente = m.foto_url ? "📷 Foto" : m.origen === "yape" ? "Yape" : "";
        return (
          <li key={i}>
            <span className={`ella-tile-ic ${c.cls}`}>{c.signo === "+" ? "↑" : c.signo === "−" ? "↓" : "?"}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="ella-mov-c">{cap(m.concepto) || "—"}</div>
              <div className={`ella-mov-t ${c.cls}`}>
                {c.l}{fuente ? ` · ${fuente}` : ""} · {fechaCorta(m.fecha)}
                {m.por_cobrar ? " · por cobrar" : ""}
              </div>
            </div>
            <strong className={c.signo === "+" ? "pos" : ""}>
              {c.signo} {soles(Number(m.monto))}
            </strong>
          </li>
        );
      })}
    </ul>
  );
}

/* ---------- Tableros ---------- */
function Tableros({ ficha }: { ficha: Ficha }) {
  const e = ficha.emprendedora!;
  const [periodo, setPeriodo] = useState<"semana" | "mes">("semana");
  const t: Totales = periodo === "semana" ? e.semana : e.mes;
  return (
    <>
      <div className="ella-seg">
        <button className={periodo === "semana" ? "on" : ""} onClick={() => setPeriodo("semana")}>Esta semana</button>
        <button className={periodo === "mes" ? "on" : ""} onClick={() => setPeriodo("mes")}>Últimas 4 semanas</button>
      </div>

      <section className="ella-card">
        <Fila l="Vendiste" v={t.ventas} cls="in" signo="+" />
        <Fila l="Gastos del negocio" v={t.gastos_negocio} cls="neg" signo="−" />
        <Fila l="Ganancia del negocio" v={t.ganancia} fuerte />
        <Fila l="Gastos personales" v={t.gastos_personales} cls="per" signo="−" />
        <Fila l="Cuotas de deuda" v={t.cuotas_deuda} cls="deu" signo="−" />
        <Fila l="Tu ahorro" v={t.ahorro} fuerte verde />
        {(t.por_cobrar > 0 || t.por_clasificar > 0) && (
          <p className="ella-muted" style={{ marginTop: 10 }}>
            {t.por_cobrar > 0 && <>Te deben {soles(t.por_cobrar)}. </>}
            {t.por_clasificar > 0 && <>Hay {soles(t.por_clasificar)} sin clasificar: respóndele al asistente.</>}
          </p>
        )}
      </section>

      <h3 className="ella-h">¿En qué se fue? · últimas 4 semanas</h3>
      <Desglose id="sec-ingreso" titulo="Ingresos" cls="in" datos={e.subcategorias_mes.ingreso} />
      <Desglose id="sec-gasto_negocio" titulo="Gastos del negocio" cls="neg" datos={e.subcategorias_mes.gasto_negocio} />
      <Desglose id="sec-gasto_personal" titulo="Gastos personales" cls="per" datos={e.subcategorias_mes.gasto_personal} />
      <Desglose id="sec-deuda" titulo="Deudas" cls="deu" datos={e.subcategorias_mes.deuda} />

      <section className="ella-card" id="sec-registros">
        <h3 className="ella-h" style={{ marginTop: 0 }}>Todos tus registros</h3>
        <ListaMovs movs={ficha.movimientos} />
      </section>
    </>
  );
}

function Fila({ l, v, cls = "", signo = "", fuerte = false, verde = false }: {
  l: string; v: number; cls?: string; signo?: string; fuerte?: boolean; verde?: boolean;
}) {
  return (
    <div className={`ella-fila ${fuerte ? "fuerte" : ""}`}>
      <span>{l}</span>
      <span className={verde ? "pos" : cls}>{signo} {soles(v)}</span>
    </div>
  );
}

function Desglose({ id, titulo, cls, datos }: { id: string; titulo: string; cls: string; datos?: Record<string, number> }) {
  const filas = Object.entries(datos ?? {}).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...filas.map(([, v]) => v), 1);
  return (
    <section className="ella-card" id={id}>
      <h3 className="ella-h" style={{ marginTop: 0 }}>{titulo}</h3>
      {!filas.length && <p className="ella-muted">Sin registros en las últimas 4 semanas.</p>}
      {filas.map(([k, v]) => (
        <div key={k} className="ella-des">
          <div className="row-sb"><span>{SUB[k] ?? k}</span><strong>{soles(v)}</strong></div>
          <div className="ella-track"><div className={`ella-fill ${cls}`} style={{ width: `${(v / max) * 100}%` }} /></div>
        </div>
      ))}
    </section>
  );
}

/* ---------- Mi crédito ---------- */
function CaminoCredito({ ficha, onClick }: { ficha: Ficha; onClick?: () => void }) {
  const ev = ficha.evaluacion;
  const e = ficha.emprendedora!;
  const avance = Math.min(100, Math.round((ev.semanas_con_datos / MIN_SEMANAS) * 100));
  const r = 34, c = 2 * Math.PI * r;
  const yape = ev.coincidencia_yape_pct;
  return (
    <section className="ella-card ella-row" onClick={onClick} style={{ cursor: onClick ? "pointer" : "default" }}>
      <svg width="88" height="88" viewBox="0 0 88 88" aria-label={`Avance ${avance}%`}>
        <circle cx="44" cy="44" r={r} fill="none" stroke="#e6efe9" strokeWidth="9" />
        <circle cx="44" cy="44" r={r} fill="none" stroke="#0E7C66" strokeWidth="9" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - avance / 100)} transform="rotate(-90 44 44)" />
        <text x="44" y="50" textAnchor="middle" fontSize="18" fontWeight="800" fill="#0F3B32">{avance}%</text>
      </svg>
      <div style={{ flex: 1 }}>
        <strong style={{ fontSize: 16 }}>Camino a tu crédito</strong>
        <ul className="ella-checks">
          <li className={ev.semanas_con_datos >= MIN_SEMANAS ? "ok" : "falta"}>
            Semanas registradas: {Math.min(ev.semanas_con_datos, MIN_SEMANAS)} de {MIN_SEMANAS}
          </li>
          <li className={e.dias_con_registro_7 >= 4 ? "ok" : "falta"}>
            Días con registro esta semana: {e.dias_con_registro_7} de 7
          </li>
          <li className={yape != null && yape >= 30 ? "ok" : "falta"}>
            Ventas por Yape: {yape == null ? "—" : `${Math.round(yape)}%`}
          </li>
        </ul>
      </div>
    </section>
  );
}

function Credito({ ficha }: { ficha: Ficha }) {
  const ev = ficha.evaluacion;
  const d = ev.decision;
  const faltan = Math.max(0, MIN_SEMANAS - ev.semanas_con_datos);
  const pasos = [
    { t: "Registra tus ventas y gastos", ok: ev.semanas_con_datos >= MIN_SEMANAS },
    { t: "Cobra por Yape (cuenta como verificado)", ok: (ev.coincidencia_yape_pct ?? 0) >= 30 },
    { t: "Paga tu primera cuota a tiempo", ok: false },
    { t: "Formalízate con el Nuevo RUS", ok: false },
  ];
  return (
    <>
      <CaminoCredito ficha={ficha} />

      <section className="ella-hero">
        <span className="ella-hero-l">Tu primer crédito con Mibanco</span>
        {ev.estado === "Faltan datos" ? (
          <>
            <div className="ella-big" style={{ fontSize: 26 }}>
              Te {faltan === 1 ? "falta 1 semana" : `faltan ${faltan} semanas`} de registros
            </div>
            <p className="ella-hero-p">Con {MIN_SEMANAS} semanas, Mibanco puede ver tu negocio y evaluarte, si tú lo autorizas.</p>
          </>
        ) : d.monto > 0 ? (
          <>
            <div className="ella-big">hasta {soles(d.monto)}</div>
            <p className="ella-hero-p">
              Cuota aprox. {soles(cuotaFrancesa(d.monto, d.plazo_meses, d.tea))} al mes por {d.plazo_meses} meses.
            </p>
          </>
        ) : (
          <>
            <div className="ella-big" style={{ fontSize: 26 }}>Sigue registrando</div>
            <p className="ella-hero-p">Cuando tu ahorro mensual alcance para una cuota, te avisamos.</p>
          </>
        )}
        <span className="ella-sim">Simulación · la oferta real la decide Mibanco</span>
      </section>

      <h3 className="ella-h">Así crece tu crédito</h3>
      <section className="ella-card">
        <ol className="ella-escalera">
          {pasos.map((p, i) => (
            <li key={i} className={p.ok ? "ok" : ""}>
              <span className="n">{p.ok ? "✓" : i + 1}</span>
              {p.t}
            </li>
          ))}
        </ol>
      </section>
    </>
  );
}
