import { useEffect, useMemo, useRef, useState } from "react";
import { getFicha, getPerfiles } from "./api";
import { BarsVentasGastos, Heatmap, LineAhorroCuota, Ring } from "./charts";
import { cuotaFrancesa, pct, soles, TEA } from "./finance";
import type { Ficha, Movimiento, ResumenPerfil } from "./types";

const iniciales = (nombre: string) =>
  (nombre || "·").split(" ").slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "").join("") || "·";

function Badge({ estado }: { estado: string }) {
  const cls = estado === "Apta" ? "apta" : estado === "En proceso" ? "proceso" : "faltan";
  return <span className={`badge ${cls}`}>{estado}</span>;
}

export default function App() {
  const [tab, setTab] = useState<"cartera" | "cliente">("cliente");
  const [toast, setToast] = useState<string | null>(null);
  const [filtro, setFiltro] = useState<string | null>(null);
  const mostrarToast = (t: string) => {
    setToast(t);
    setTimeout(() => setToast(null), 2600);
  };
  const irACliente = (f: string | null) => {
    setFiltro(f);
    setTab("cliente");
  };
  return (
    <>
      <header className="header">
        <span className="marca">Visible para analistas</span>
        <span className="sub">· Mibanco · simulación</span>
        <nav className="tabs">
          <button className={`tab ${tab === "cartera" ? "activo" : ""}`} onClick={() => { setFiltro(null); setTab("cartera"); }}>Cartera</button>
          <button className={`tab ${tab === "cliente" ? "activo" : ""}`} onClick={() => { setFiltro(null); setTab("cliente"); }}>Por cliente</button>
        </nav>
      </header>
      <main className="wrap">
        {tab === "cartera"
          ? <Cartera onNavegar={irACliente} />
          : <PorCliente onToast={mostrarToast} filtro={filtro} onLimpiarFiltro={() => setFiltro(null)} />}
      </main>
      {toast && <div className="toast">{toast}</div>}
    </>
  );
}

/* ---------- Pantalla 7: Cartera ---------- */
const KPIS_RETO = [
  { l: "Emprendedoras con perfil crediticio", v: "58%" },
  { l: "Aptas para su primer crédito", v: "1 146" },
  { l: "Precisión de lectura (IA)", v: "72%" },
  { l: "Cartera potencial a 6 meses", v: "S/ 12.9 M" },
];
const ALERTAS = [
  { color: "#15803d", n: "19", t: "nuevas con 4 semanas completas", accion: "Ofrecer crédito", filtro: "Apta" },
  { color: "#b91c1c", n: "7", t: "con caída de ventas > 20%", accion: "Revisar", filtro: null },
  { color: "#2a4ba8", n: "41", t: "aptas sin oferta enviada", accion: "Enviar oferta", filtro: "Apta" },
  { color: "#b45309", n: "33", t: "en proceso de registro", accion: "Seguimiento", filtro: "En proceso" },
  { color: "#6b7280", n: "2", t: "Posible duplicado", accion: "Revisar fotos", filtro: null },
];

function Cartera({ onNavegar }: { onNavegar: (f: string | null) => void }) {
  const [sub, setSub] = useState("resumen");
  return (
    <div className="stack">
      <div className="card">
        <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ fontSize: 30, fontWeight: 800 }}>12 480 <span className="muted" style={{ fontSize: 16, fontWeight: 600 }}>emprendedoras</span></div>
            <div className="row" style={{ gap: 7, marginTop: 8 }}>
              <span className="pill" style={{ background: "#e7f5ec", color: "#15803d" }}>✓ con permiso</span>
              <span className="chip">último mes</span>
              <span className="pill">63% de ventas por Yape (verificable)</span>
            </div>
          </div>
          <span className="simLabel">Datos simulados del piloto</span>
        </div>
        <div className="inner-tabs" style={{ marginTop: 14 }}>
          {[["resumen", "Resumen"], ["demanda", "Demanda"], ["seguimiento", "Seguimiento"]].map(([k, l]) => (
            <button key={k} className={`itab ${sub === k ? "activo" : ""}`} onClick={() => setSub(k)}>{l}</button>
          ))}
        </div>
      </div>

      {sub === "resumen" && (
        <>
          <div className="kpis kpis5">
            {KPIS_RETO.map((k) => (
              <div className="card kpi" key={k.l}>
                <span className="reto">KPI reto</span>
                <div className="v">{k.v}</div>
                <div className="l">{k.l}</div>
              </div>
            ))}
            <div className="card kpi">
              <div className="v" style={{ color: "#15803d" }}>2.4%</div>
              <div className="l">Mora del piloto · <span className="up">●</span> verde</div>
            </div>
          </div>

          <div className="card">
            <h3>Alertas de hoy · automáticas</h3>
            <div className="alertas-grid">
              {ALERTAS.map((a, i) => (
                <button key={i} className="alerta-card" style={{ borderTopColor: a.color }} onClick={() => onNavegar(a.filtro)}>
                  <div className="alerta-n" style={{ color: a.color }}>{a.n}</div>
                  <div className="alerta-t">{a.t}</div>
                  <div className="alerta-a">→ {a.accion}</div>
                </button>
              ))}
            </div>
          </div>
        </>
      )}

      {sub === "demanda" && (
        <div className="card">
          <h3>Demanda de crédito</h3>
          <p className="muted">1 146 aptas · S/ 12.9 M en solicitudes potenciales · ticket promedio S/ 1 100.</p>
          <p className="muted">Concentración: Gamarra (ropa) y SJL (bodegas). Datos simulados del piloto.</p>
        </div>
      )}
      {sub === "seguimiento" && (
        <div className="card">
          <h3>Seguimiento de repago</h3>
          <p className="muted">Mora 2.4% · 312 créditos vigentes · 98% de cuotas al día. Datos simulados del piloto.</p>
        </div>
      )}
    </div>
  );
}

/* ---------- Pantalla 5: Por cliente ---------- */
function PorCliente({ onToast, filtro, onLimpiarFiltro }: {
  onToast: (t: string) => void; filtro: string | null; onLimpiarFiltro: () => void;
}) {
  const [perfiles, setPerfiles] = useState<ResumenPerfil[]>([]);
  const [sel, setSel] = useState<string | null>(null);
  const [ficha, setFicha] = useState<Ficha | null>(null);
  const [itab, setItab] = useState("resumen");
  const visibles = filtro ? perfiles.filter((p) => p.estado === filtro) : perfiles;

  useEffect(() => {
    getPerfiles().then((ps) => {
      setPerfiles(ps);
      if (ps.length && !sel) setSel(ps[0].id);
    });
  }, []);

  // Ficha + auto-refresco cada 10s para ver entrar la foto recién enviada.
  const refFicha = useRef<string | null>(null);
  refFicha.current = sel;
  useEffect(() => {
    if (!sel) return;
    let activo = true;
    const cargar = () => getFicha(sel).then((f) => activo && refFicha.current === sel && setFicha(f));
    cargar();
    const id = setInterval(cargar, 10000);
    return () => { activo = false; clearInterval(id); };
  }, [sel]);

  return (
    <div className="cliente">
      <aside className="card lista">
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ margin: 0 }}>Autorizadas</h3>
          {filtro && (
            <button className="itab activo" onClick={onLimpiarFiltro} style={{ fontSize: 12 }}>
              {filtro} ✕
            </button>
          )}
        </div>
        {visibles.map((p) => (
          <div key={p.id} className={`lista-item ${p.id === sel ? "sel" : ""}`} onClick={() => { setSel(p.id); setItab("resumen"); }}>
            <div className="ini">{iniciales(p.nombre || p.telefono_mascara)}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="nom">{p.nombre || p.telefono_mascara}</div>
              <div className="muted" style={{ fontSize: 12 }}>{p.rubro} · {p.zona}</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontWeight: 800 }}>{p.puntaje ?? "—"}</div>
              <Badge estado={p.estado} />
            </div>
          </div>
        ))}
      </aside>

      {ficha ? <FichaCliente ficha={ficha} itab={itab} setItab={setItab} onToast={onToast} /> : <div className="card">Cargando…</div>}
    </div>
  );
}

function FichaCliente({ ficha, itab, setItab, onToast }: {
  ficha: Ficha; itab: string; setItab: (t: string) => void; onToast: (t: string) => void;
}) {
  const ev = ficha.evaluacion;
  const tabs = [
    ["resumen", "Resumen"], ["movimientos", "Movimientos"], ["senales", "Señales"],
    ["confiabilidad", "Confiabilidad"], ["plan", "Plan"], ["simulador", "Simulador"],
  ];
  return (
    <>
      <section className="stack">
        <div className="card">
          <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <h2 style={{ marginBottom: 6 }}>{ficha.nombre || ficha.telefono_mascara}</h2>
              <div className="row" style={{ gap: 7 }}>
                <span className="chip">{ficha.rubro || "—"}</span>
                <span className="chip">{ficha.zona || "—"}</span>
                <span className="chip">Sin RUC</span>
                {ficha.consentimiento && <span className="chip">✓ Consentimiento · {ficha.consentimiento}</span>}
                <span className="chip">{ficha.telefono_mascara}</span>
              </div>
            </div>
            <div style={{ textAlign: "center" }}>
              <Ring score={ev.puntaje} />
              <Badge estado={ev.estado} />
            </div>
          </div>
        </div>

        <div className="kpis">
          <Kpi l="Ventas / semana" v={soles(ev.ventas_semana_promedio)}
            extra={<span className={ev.tendencia_pct >= 0 ? "up" : "down"}>{ev.tendencia_pct >= 0 ? "▲" : "▼"} {pct(Math.abs(ev.tendencia_pct))}</span>} />
          <Kpi l="Estabilidad" v={ev.estabilidad} extra={<span className="muted">CV {pct(ev.coef_variacion_pct)}</span>} />
          <Kpi l="Constancia" v={`${ev.dias_con_registro} / 28 días`} extra={<span className="muted">registro</span>} />
          <Kpi l="Coincide con Yape" v={ev.coincidencia_yape_pct == null ? "—" : pct(ev.coincidencia_yape_pct)} extra={<span className="muted">verificable</span>} />
        </div>

        <div className="card">
          <div className="inner-tabs">
            {tabs.map(([k, l]) => (
              <button key={k} className={`itab ${itab === k ? "activo" : ""}`} onClick={() => setItab(k)}>{l}</button>
            ))}
          </div>
          {itab === "resumen" && <Resumen ev={ev} />}
          {itab === "movimientos" && <TablaMovimientos movs={ficha.movimientos} />}
          {itab === "senales" && <Señales ev={ev} />}
          {itab === "confiabilidad" && <Confiabilidad ev={ev} />}
          {itab === "plan" && <Plan ev={ev} />}
          {itab === "simulador" && <Simulador baseMensual={ev.base_mensual} />}
        </div>
      </section>

      <Decision ev={ev} onToast={onToast} onSimular={() => setItab("simulador")} />
    </>
  );
}

function Kpi({ l, v, extra }: { l: string; v: string; extra?: React.ReactNode }) {
  return (
    <div className="card kpi">
      <div className="v">{v}</div>
      <div className="l">{l} · {extra}</div>
    </div>
  );
}

function Resumen({ ev }: { ev: Ficha["evaluacion"] }) {
  return (
    <div className="grid2">
      <div>
        <h3>Ventas vs gastos (4 semanas)</h3>
        <BarsVentasGastos ventas={ev.ventas_por_semana} gastos={ev.gastos_por_semana} />
        <div className="row" style={{ gap: 14, marginTop: 6 }}>
          <span className="pill" style={{ background: "#eaf0fb", color: "#2a4ba8" }}>■ ventas</span>
          <span className="pill" style={{ background: "#fdeaea", color: "#b91c1c" }}>■ gastos</span>
        </div>
      </div>
      <div>
        <h3>¿Cuándo cobra?</h3>
        <Heatmap matrix={ev.heatmap} />
      </div>
    </div>
  );
}

function TablaMovimientos({ movs }: { movs: Movimiento[] }) {
  if (!movs.length) return <p className="muted">Sin movimientos registrados.</p>;
  return (
    <table>
      <thead>
        <tr><th>Fecha</th><th>Concepto</th><th>Categoría</th><th>Origen</th><th>Confianza</th><th>Monto</th><th>Foto</th></tr>
      </thead>
      <tbody>
        {movs.map((m, i) => (
          <tr key={i}>
            <td>{m.fecha}</td>
            <td>{m.concepto}</td>
            <td><span className={`tag ${m.categoria}`}>{m.categoria}</span>{m.por_cobrar && <span className="muted"> · por cobrar</span>}</td>
            <td>{m.origen === "yape" ? "Yape/Plin" : m.origen || "—"}</td>
            <td>{m.confianza == null ? "—" : `${Math.round(Number(m.confianza) * 100)}%`}</td>
            <td>{soles(Number(m.monto))}</td>
            <td>{m.foto_url ? <a href={m.foto_url} target="_blank" rel="noreferrer">ver</a> : "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Señales({ ev }: { ev: Ficha["evaluacion"] }) {
  const items = Object.entries(ev.subpuntajes);
  return (
    <div className="stack">
      {items.map(([k, v]) => (
        <div key={k}>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <span style={{ textTransform: "capitalize" }}>{k} · peso {ev.pesos[k]}</span>
            <strong>{Math.round(v * 100)}%</strong>
          </div>
          <div style={{ background: "#f1efe9", borderRadius: 8, height: 10, marginTop: 4 }}>
            <div style={{ width: `${v * 100}%`, background: "#2a4ba8", height: 10, borderRadius: 8 }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function Confiabilidad({ ev }: { ev: Ficha["evaluacion"] }) {
  return (
    <div className="stack">
      <p>Semanas con registro: <strong>{ev.semanas_con_datos} / 4</strong></p>
      <p>Ventas verificadas por Yape/Plin: <strong>{ev.coincidencia_yape_pct == null ? "—" : pct(ev.coincidencia_yape_pct)}</strong></p>
      <p>Variación de ventas (CV): <strong>{pct(ev.coef_variacion_pct)}</strong> → {ev.estabilidad}</p>
      <div className="alert">
        <span className="dot" style={{ background: "#2a4ba8" }} />
        <span><strong>Antiduplicados activo:</strong> cada foto se registra una sola vez (huella SHA-256 por usuaria); las capturas repetidas se descartan.</span>
      </div>
      <p className="muted">La confiabilidad sube con más semanas de registro y más pagos digitales verificables.</p>
    </div>
  );
}

function Plan({ ev }: { ev: Ficha["evaluacion"] }) {
  const pasos = ev.estado === "Apta"
    ? ["Ofrecer el monto sugerido con plazo 6 meses.", "Acompañar el primer repago.", "Subir de monto al cumplir 3 cuotas."]
    : ["Registrar 4 semanas completas de ventas.", "Priorizar cobros por Yape/Plin (verificable).", "Separar gasto del negocio del gasto de casa."];
  return <ol>{pasos.map((p, i) => <li key={i} style={{ marginBottom: 8 }}>{p}</li>)}</ol>;
}

function Decision({ ev, onToast, onSimular }: { ev: Ficha["evaluacion"]; onToast: (t: string) => void; onSimular: () => void }) {
  const d = ev.decision;
  const verif = ev.coincidencia_yape_pct ?? 0;
  return (
    <aside className="card decision stack">
      <h3>Decisión sugerida</h3>
      {d.monto > 0 ? (
        <>
          <div className="monto">{soles(d.monto)}</div>
          <div>
            <div className="fila"><span className="muted">Cuota mensual</span><strong>{soles(d.cuota)}</strong></div>
            <div className="fila"><span className="muted">Plazo</span><strong>{d.plazo_meses} meses</strong></div>
            <div className="fila"><span className="muted">TEA</span><strong>{Math.round(d.tea * 100)}%</strong></div>
            <div className="fila"><span className="muted">Verificado vs efectivo</span><strong>{Math.round(verif)}% / {Math.round(100 - verif)}%</strong></div>
            <div className="fila"><span className="muted">Cuota / excedente</span><strong>{d.ratio_cuota_excedente == null ? "—" : pct(d.ratio_cuota_excedente * 100)}</strong></div>
          </div>
        </>
      ) : (
        <p className="muted">Aún sin capacidad de pago suficiente para un monto del catálogo.</p>
      )}
      <button className="btn primary" onClick={() => onToast("✅ Oferta enviada (simulación)")}>Ofrecer crédito</button>
      <button className="btn ghost" onClick={onSimular}>Simular</button>
    </aside>
  );
}

/* ---------- Pantalla 6: Simulador ---------- */
function Simulador({ baseMensual }: { baseMensual: number }) {
  const [monto, setMonto] = useState(800);
  const [plazo, setPlazo] = useState(6);
  const [escenario, setEscenario] = useState(0); // 0, 0.1, 0.2
  const [reemplaza, setReemplaza] = useState(false);
  const DEUDA_INFORMAL = 200;

  const r = useMemo(() => {
    const cuota = cuotaFrancesa(monto, plazo);
    const baseEsc = baseMensual * (1 - escenario);
    const libre = baseEsc + (reemplaza ? DEUDA_INFORMAL : 0);
    const ratio = libre > 0 ? cuota / libre : Infinity;
    const color = ratio <= 0.1 ? "#15803d" : ratio <= 0.2 ? "#b45309" : "#b91c1c";
    return { cuota, libre, ratio, color };
  }, [monto, plazo, escenario, reemplaza, baseMensual]);

  return (
    <div className="grid2">
      <div>
        <div className="control">
          <label>Monto: <strong>{soles(monto)}</strong></label>
          <input type="range" min={500} max={3000} step={100} value={monto} onChange={(e) => setMonto(+e.target.value)} />
        </div>
        <div className="control">
          <label>Plazo</label>
          <div className="seg">
            {[3, 6, 9, 12].map((p) => (
              <button key={p} className={plazo === p ? "on" : ""} onClick={() => setPlazo(p)}>{p} m</button>
            ))}
          </div>
        </div>
        <div className="control">
          <label>Escenario</label>
          <div className="seg">
            {[["Normal", 0], ["Ventas −10%", 0.1], ["Ventas −20%", 0.2]].map(([l, v]) => (
              <button key={l as string} className={escenario === v ? "on" : ""} onClick={() => setEscenario(v as number)}>{l}</button>
            ))}
          </div>
        </div>
        <div className="control">
          <label><input type="checkbox" checked={reemplaza} onChange={(e) => setReemplaza(e.target.checked)} /> Reemplazar deuda informal (libera {soles(DEUDA_INFORMAL)}/mes)</label>
        </div>
      </div>
      <div className="stack">
        <div className="card">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <div><div className="l muted">Cuota mensual</div><div className="v" style={{ fontSize: 24, fontWeight: 800 }}>{soles(r.cuota)}</div></div>
            <div><div className="l muted">Libre al mes</div><div className="v" style={{ fontSize: 24, fontWeight: 800 }}>{soles(r.libre)}</div></div>
            <div style={{ textAlign: "right" }}>
              <div className="l muted">Cuota / excedente</div>
              <div className="v" style={{ fontSize: 24, fontWeight: 800, color: r.color }}>
                <span className="sem" style={{ background: r.color, marginRight: 8 }} />
                {isFinite(r.ratio) ? pct(r.ratio * 100) : "—"}
              </div>
            </div>
          </div>
        </div>
        <div className="card">
          <h3>Ahorro semanal vs cuota</h3>
          <LineAhorroCuota ahorro={r.libre / 4.33} cuota={r.cuota / 4.33} />
        </div>
      </div>
    </div>
  );
}
