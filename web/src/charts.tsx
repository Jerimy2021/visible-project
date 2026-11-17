const VERDE = "#1f9d5c";
const AMBAR = "#ffc20e";
const ROJO = "#e0282c";
const NARANJA = "#ff8a00";
const MUT = "#4a5462";

const color = (p: number) => (p >= 95 ? VERDE : p >= 70 ? AMBAR : ROJO);

export function Gauge({ pct, inspeccionados, total }: { pct: number; inspeccionados: number; total: number }) {
  const r = 85, c = Math.PI * r; // semicírculo
  const off = c * (1 - pct / 100);
  return (
    <svg viewBox="0 0 220 150" width="100%" style={{ maxWidth: 260 }}>
      <path d="M25 125 A85 85 0 0 1 195 125" fill="none" stroke="#e6e9ed" strokeWidth="22" strokeLinecap="round" />
      <path
        d="M25 125 A85 85 0 0 1 195 125" fill="none" stroke={color(pct)} strokeWidth="22"
        strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off}
        style={{ transition: "stroke-dashoffset .7s ease" }}
      />
      <text x="110" y="112" textAnchor="middle" fontSize="44" fontWeight="800" fill="#14171c">{pct}%</text>
      <text x="110" y="134" textAnchor="middle" fontSize="12" fill={MUT}>{inspeccionados} de {total} del mes</text>
    </svg>
  );
}

export function BarsH({ data }: { data: { nombre: string; valor: number; total: number; sub?: string }[] }) {
  return (
    <div className="stack">
      {data.map((d, i) => {
        const pct = d.total ? Math.round((100 * d.valor) / d.total) : 0;
        return (
          <div key={i}>
            <div className="row" style={{ justifyContent: "space-between", marginBottom: 3 }}>
              <strong style={{ fontSize: 13 }}>{d.nombre}</strong>
              <span style={{ fontSize: 12, color: MUT }}>{d.sub ?? `${d.valor}/${d.total}`} · <b>{pct}%</b></span>
            </div>
            <div className="bar-track" style={{ height: 16 }}>
              <div className="bar-fill" style={{ width: `${pct}%`, background: color(pct) }} />
            </div>
          </div>
        );
      })}
      {data.length === 0 && <p style={{ color: MUT }}>Sin datos en el periodo.</p>}
    </div>
  );
}

export function Tendencia({ serie }: { serie: { periodo: string; avance_pct: number }[] }) {
  const w = 460, h = 180, pad = 28, n = serie.length;
  const bw = (w - pad * 2) / n;
  const y = (v: number) => h - pad - (v / 100) * (h - pad * 2);
  const meta = y(100);
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%">
      <line x1={pad} y1={meta} x2={w - pad} y2={meta} stroke={VERDE} strokeWidth="2" strokeDasharray="6 5" />
      <text x={w - pad} y={meta - 6} textAnchor="end" fontSize="10" fill={MUT}>meta 100%</text>
      {serie.map((s, i) => {
        const ult = i === n - 1;
        const bx = pad + i * bw;
        const bh = h - pad - y(s.avance_pct);
        return (
          <g key={i}>
            <rect x={bx + bw * 0.2} y={y(s.avance_pct)} width={bw * 0.6} height={Math.max(bh, 1)} rx="3"
              fill={ult ? ROJO : MUT} style={{ transition: "y .5s, height .5s" }} />
            <text x={bx + bw / 2} y={y(s.avance_pct) - 5} textAnchor="middle" fontSize={ult ? 13 : 11}
              fontWeight="800" fill={ult ? ROJO : MUT}>{s.avance_pct}%</text>
            <text x={bx + bw / 2} y={h - pad + 15} textAnchor="middle" fontSize="10" fill={MUT}>
              {s.periodo.slice(5)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export function PuntoFalla({ data }: { data: { punto: string; p: number }[] }) {
  const max = Math.max(1, ...data.map((d) => d.p));
  return (
    <div className="stack" style={{ gap: 7 }}>
      {data.map((d, i) => (
        <div key={d.punto} className="row">
          <span style={{ width: 92, fontSize: 12, fontWeight: i === 0 && d.p > 0 ? 800 : 400 }}>{d.punto}</span>
          <div className="bar-track" style={{ height: 11 }}>
            <div className="bar-fill" style={{ width: `${(100 * d.p) / max}%`, background: i === 0 && d.p > 0 ? "#d9161a" : i < 3 ? NARANJA : "#9aa3ae" }} />
          </div>
          <b style={{ width: 20, textAlign: "right" }}>{d.p}</b>
        </div>
      ))}
    </div>
  );
}
