import { useEffect, useState } from "react";
import { getCentro, getExtintor, getExtintores, subirCsv } from "./api";
import { BarsH, Gauge, PuntoFalla, Tendencia } from "./charts";
import type { Centro, ExtintorRow, Ficha } from "./types";

const PERIODOS = ["2026-11", "2026-10", "2026-09", "2026-08", "2026-07", "2026-06"];
const NAV = [
  ["centro", "📊", "Centro de control", true],
  ["extintores", "🧯", "Extintores", true],
  ["subir", "⬆️", "Subir CSV", true],
  ["reportes", "📄", "Reportes", false],
  ["levantar", "🛠️", "Levantar", false],
  ["plano", "🗺️", "Plano", false],
] as const;

export default function App() {
  const [vista, setVista] = useState("centro");
  const [toast, setToast] = useState<string | null>(null);
  const aviso = (t: string) => { setToast(t); setTimeout(() => setToast(null), 3000); };
  return (
    <div className="app">
      <aside className="side">
        <div className="marca"><b>BRIGADA SSOMA</b><span>CONTROL DE EXTINTORES</span></div>
        <nav>
          {NAV.map(([k, ic, label, ok]) => (
            <button key={k} className={`${vista === k ? "on" : ""} ${ok ? "" : "dis"}`}
              onClick={() => ok && setVista(k)}>
              <span className="ic">{ic}</span>{label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="main">
        <div className="ribbon" />
        <div className="top">
          <h1>CENTRO DE CONTROL · INSPECCIONES</h1>
          <p>Mantenimiento mensual de extintores por brigadas · Alicorp</p>
        </div>
        <div className="wrap">
          {vista === "centro" && <CentroVista />}
          {vista === "extintores" && <ExtintoresVista />}
          {vista === "subir" && <SubirVista aviso={aviso} />}
          {["reportes", "levantar", "plano"].includes(vista) && (
            <div className="card">Pantalla “{NAV.find((n) => n[0] === vista)?.[2]}” — próximamente.</div>
          )}
        </div>
      </main>
      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}

function Kpi({ l, v, s, c }: { l: string; v: string | number; s: string; c: string }) {
  return (
    <div className="card kpi">
      <div className="bar" style={{ background: c }} />
      <div className="l">{l}</div>
      <div className="v">{v}</div>
      <div className="s">{s}</div>
    </div>
  );
}

function CentroVista() {
  const [site, setSite] = useState("HUA");
  const [periodo, setPeriodo] = useState("2026-11");
  const [c, setC] = useState<Centro | null>(null);
  useEffect(() => { getCentro(site, periodo).then(setC).catch(() => setC(null)); }, [site, periodo]);
  if (!c) return <div className="card">Cargando…</div>;
  const ap = c.aprobacion.estado ?? `${c.aprobacion.aprobadas}/${c.aprobacion.plantas}`;
  return (
    <div className="stack">
      <div className="filtros">
        <div className="campo"><label>PLANTA</label>
          <select value={site} onChange={(e) => setSite(e.target.value)}>
            <option value="HUA">HUA · CD Huachipa</option><option value="Todas">Todas</option>
          </select></div>
        <div className="campo"><label>PERIODO</label>
          <select value={periodo} onChange={(e) => setPeriodo(e.target.value)}>
            {PERIODOS.map((p) => <option key={p}>{p}</option>)}
          </select></div>
      </div>

      <div className="grid g-top">
        <div className="card" style={{ display: "grid", placeItems: "center" }}>
          <h3>AVANCE DE INSPECCIÓN</h3>
          <Gauge pct={c.avance_pct} inspeccionados={c.inspeccionados} total={c.total} />
          <div className="row" style={{ gap: 8, marginTop: 6 }}>
            <span className="pill" style={{ background: "#fff3e0", color: "#8a4300" }}>{c.faltan} por inspeccionar</span>
            <span className="pill" style={{ background: "#fdeaea", color: "#b3191d" }}>{c.p_abiertos} P abiertos</span>
          </div>
        </div>
        <div className="grid g-kpis">
          <Kpi l="EXTINTORES" v={c.total} s="en el alcance" c="#14171c" />
          <Kpi l="INSPECCIONADOS" v={c.inspeccionados} s="en el periodo" c="#1f9d5c" />
          <Kpi l="FALTAN" v={c.faltan} s="del mes" c="#ffc20e" />
          <Kpi l="CONFORMES A LA 1ª" v={c.conformes_1a_pct == null ? "—" : `${c.conformes_1a_pct}%`} s="sin ningún P" c="#1f9d5c" />
          <Kpi l="P ABIERTOS" v={c.p_abiertos} s="sin levantar" c="#e0282c" />
          <Kpi l="TIEMPO LEVANTAM." v={c.tiempo_levantamiento_dias == null ? "—" : `${c.tiempo_levantamiento_dias} d`} s="promedio" c="#1f6fd1" />
          <Kpi l="INSPECTORES" v={c.inspectores_activos} s="activos" c="#14171c" />
          <Kpi l="APROBACIÓN" v={ap} s="del mes" c="#ff8a00" />
        </div>
      </div>

      <div className="grid g-2">
        <div className="card"><h3>AVANCE POR PLANTA</h3>
          <BarsH data={c.por_planta.map((p) => ({ nombre: p.nombre, valor: p.inspeccionados, total: p.total }))} /></div>
        <div className="card"><h3>AVANCE POR INSPECTOR</h3>
          <BarsH data={c.por_inspector.map((i) => ({ nombre: i.inspector, valor: i.hechos, total: i.asignados || i.hechos || 1, sub: `${i.hechos}/${i.asignados}` }))} /></div>
      </div>

      <div className="grid g-2">
        <div className="card"><h3>TENDENCIA · 6 MESES</h3><Tendencia serie={c.tendencia} /></div>
        <div className="card"><h3>PUNTO QUE MÁS FALLA</h3><PuntoFalla data={c.punto_que_mas_falla} /></div>
      </div>

      <div className="card"><h3>TABLERO DE ALERTAS</h3>
        <div className="stack">
          {c.alertas.pendientes.map((p) => (
            <div key={p.codigo} className="alerta">
              <span className="dot" style={{ background: (p.dias_abierto ?? 0) > 15 ? "#e0282c" : "#ff8a00" }} />
              <div><div className="n">{p.codigo}</div><div style={{ fontSize: 11, color: "#4a5462" }}>P en: {p.puntos_p.join(", ") || "—"}</div></div>
              <span className="chip-estado" style={{ background: (p.dias_abierto ?? 0) > 15 ? "#d9161a" : "#ff8a00" }}>ABIERTO {p.dias_abierto} D</span>
            </div>
          ))}
          {c.alertas.reincidentes.map((r) => (
            <div key={r.codigo} className="alerta">
              <span className="dot" style={{ background: "#14171c" }} />
              <div><div className="n">{r.codigo}</div><div style={{ fontSize: 11, color: "#4a5462" }}>reincidente</div></div>
              <span className="chip-estado" style={{ background: "#14171c" }}>P EN {r.meses} MESES</span>
            </div>
          ))}
          {c.alertas.pendientes.length + c.alertas.reincidentes.length === 0 &&
            <p style={{ color: "#17804a", fontWeight: 700 }}>✔ Sin pendientes ni reincidencias.</p>}
        </div>
      </div>
    </div>
  );
}

const ESTADOS = ["", "POR HACER", "ATRASADO", "HECHO"];
function ExtintoresVista() {
  const [estado, setEstado] = useState("");
  const [rows, setRows] = useState<ExtintorRow[]>([]);
  const [ficha, setFicha] = useState<Ficha | null>(null);
  useEffect(() => { getExtintores("HUA", estado).then(setRows).catch(() => setRows([])); }, [estado]);
  return (
    <div className="stack">
      <div className="filtros">
        <div className="campo"><label>ESTADO</label>
          <select value={estado} onChange={(e) => setEstado(e.target.value)}>
            {ESTADOS.map((e) => <option key={e} value={e}>{e || "Todos"}</option>)}
          </select></div>
        <span style={{ color: "#fff", fontWeight: 700 }}>{rows.length} extintores</span>
      </div>
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table>
          <thead><tr><th>Código</th><th>Piso</th><th>Ubicación</th><th>Zona</th><th>Inspector</th><th>Estado</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.codigo} onClick={() => getExtintor(r.codigo).then(setFicha)}>
                <td><b>{r.codigo}</b></td><td>{r.piso}</td><td>{r.ubicacion}</td><td>{r.zona_brigada}</td>
                <td>{r.inspector_asignado}</td>
                <td><span className={`tag ${r.estado_inspeccion === "POR HACER" ? "POR" : r.estado_inspeccion}`}>{r.estado_inspeccion}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {ficha && <FichaModal ficha={ficha} cerrar={() => setFicha(null)} />}
    </div>
  );
}

function FichaModal({ ficha, cerrar }: { ficha: Ficha; cerrar: () => void }) {
  const e = ficha.extintor as Record<string, string>;
  return (
    <div className="modal" onClick={cerrar}>
      <div className="box" onClick={(ev) => ev.stopPropagation()}>
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h3 style={{ fontSize: 18 }}>{e.codigo} · {e.ubicacion}</h3>
          <button className="btn gh" onClick={cerrar}>Cerrar</button>
        </div>
        <p style={{ color: "#4a5462" }}>{e.tipo} {e.capacidad} {e.unidad_capacidad} · {e.marca} · zona {e.zona_brigada} · estado {e.estado}</p>
        <h3 style={{ marginTop: 14 }}>HISTORIAL</h3>
        <table>
          <thead><tr><th>Periodo</th><th>Inspector</th><th>Resultado</th><th>P</th><th>Fecha</th></tr></thead>
          <tbody>
            {ficha.historial.map((m: Record<string, unknown>, i) => (
              <tr key={i}><td>{String(m.periodo)}</td><td>{String(m.inspector)}</td><td>{String(m.resultado)}</td>
                <td>{String(m.cantidad_p)}</td><td>{String(m.fecha_inspeccion || "")}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const ARCHIVOS = ["sites.csv", "Extintores.csv", "MantenimientosMensuales.csv", "AprobacionesMes.csv"];
function SubirVista({ aviso }: { aviso: (t: string) => void }) {
  const [archivo, setArchivo] = useState(ARCHIVOS[1]);
  const [estado, setEstado] = useState("");
  async function onFile(f: File | null) {
    if (!f) return;
    setEstado("Subiendo…");
    try {
      await subirCsv(archivo, f);
      setEstado(`✓ ${archivo} subido. Se procesa en segundos; revisa el Centro de control.`);
      aviso("CSV subido correctamente");
    } catch (e) { setEstado(`Error: ${(e as Error).message}`); }
  }
  return (
    <div className="card stack" style={{ maxWidth: 620 }}>
      <h3>SUBIR LISTA (CSV)</h3>
      <p style={{ color: "#4a5462" }}>Exporta la lista de SharePoint y súbela aquí. El sistema la actualiza sola.</p>
      <div className="campo"><label>LISTA</label>
        <select value={archivo} onChange={(e) => setArchivo(e.target.value)}>
          {ARCHIVOS.map((a) => <option key={a}>{a}</option>)}
        </select></div>
      <label className="drop">
        <input type="file" accept=".csv" style={{ display: "none" }} onChange={(e) => onFile(e.target.files?.[0] ?? null)} />
        <div style={{ fontWeight: 800 }}>Haz clic para elegir el CSV</div>
        <div style={{ color: "#4a5462", fontSize: 12 }}>se sube como “{archivo}”</div>
      </label>
      {estado && <div className="pill" style={{ background: "#eef1f4", color: "#14171c", alignSelf: "flex-start" }}>{estado}</div>}
    </div>
  );
}
