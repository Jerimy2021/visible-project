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
  const mostrarToast = (t: string) => {
    setToast(t);
    setTimeout(() => setToast(null), 2600);
  };
  return (
    <>
      <header className="header">
        <span className="marca">Visible para analistas</span>
        <span className="sub">· BCP · simulación</span>
        <nav className="tabs">
          <button className={`tab ${tab === "cartera" ? "activo" : ""}`} onClick={() => setTab("cartera")}>Cartera</button>
          <button className={`tab ${tab === "cliente" ? "activo" : ""}`} onClick={() => setTab("cliente")}>Por cliente</button>
        </nav>
      </header>
      <main className="wrap">
        {tab === "cartera" ? <Cartera /> : <PorCliente onToast={mostrarToast} />}
      </main>
      {toast && <div className="toast">{toast}</div>}
    </>
  );
}

/* ---------- Pantalla 7: Cartera (datos simulados fijos) ---------- */
function Cartera() {
  const kpis = [
    { l: "Autorizadas activas", v: "128" },
    { l: "Aptas para crédito", v: "41" },
    { l: "Monto desembolsable", v: "S/ 82,400" },
    { l: "Mora piloto", v: "2.3%" },
  ];
  const alertas = [
    { c: "#15803d", t: "19 nuevas emprendedoras con 4 semanas completas esta semana." },
    { c: "#b45309", t: "7 perfiles con caída de ventas > 20% — revisar antes de ofrecer." },
    { c: "#2a4ba8", t: "63% de las ventas registradas llegan por Yape/Plin (verificable)." },
    { c: "#b91c1c", t: "2 perfiles con páginas de cuaderno repetidas — posible duplicado." },
  ];
  return (
    <div className="stack">
      <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>Cartera del piloto</h2>
        <span className="simLabel">Datos simulados del piloto</span>
      </div>
      <div className="kpis">
        {kpis.map((k) => (
          <div className="card kpi" key={k.l}>
            <div className="v">{k.v}</div>
            <div className="l">{k.l}</div>
          </div>
        ))}
      </div>
      <div className="grid2">
        <div className="card">
          <h3>Distribución por estado</h3>
          <BarsDistribucion />
        </div>
        <div className="card">
          <h3>Alertas operativas</h3>
          <div className="stack" style={{ marginTop: 4 }}>
            {alertas.map((a, i) => (
              <div className="alert" key={i}>
                <span className="dot" style={{ background: a.c }} />
                <span>{a.t}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function BarsDistribucion() {
  const data = [
    { l: "Apta", v: 41, c: "#15803d" },
    { l: "En proceso", v: 54, c: "#b45309" },
    { l: "Faltan datos", v: 33, c: "#9aa0ab" },
  ];
  const max = Math.max(...data.map((d) => d.v));
  return (
    <div className="stack" style={{ marginTop: 4 }}>
      {data.map((d) => (
        <div key={d.l}>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <span className="muted">{d.l}</span>
            <strong>{d.v}</strong>
          </div>
          <div style={{ background: "#f1efe9", borderRadius: 8, height: 12, marginTop: 4 }}>
            <div style={{ width: `${(d.v / max) * 100}%`, background: d.c, height: 12, borderRadius: 8 }} />
          </div>
        </div>
      ))}
    </div>
  );
}

/* ---------- Pantalla 5: Por cliente ---------- */
function PorCliente({ onToast }: { onToast: (t: string) => void }) {
  const [perfiles, setPerfiles] = useState<ResumenPerfil[]>([]);
  const [sel, setSel] = useState<string | null>(null);
  const [ficha, setFicha] = useState<Ficha | null>(null);
  const [itab, setItab] = useState("resumen");

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
        <h3>Autorizadas</h3>
        {perfiles.map((p) => (
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
