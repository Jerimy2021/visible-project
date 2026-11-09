const AZUL = "#2a4ba8";
const MARINO = "#16264a";
const ROJO = "#d4504e";

export function Ring({ score }: { score: number | null }) {
  const r = 46;
  const c = 2 * Math.PI * r;
  const v = score ?? 0;
  const off = c * (1 - v / 100);
  const color = v >= 70 ? "#15803d" : v >= 50 ? "#b45309" : "#9aa0ab";
  return (
    <svg width="120" height="120" viewBox="0 0 120 120">
      <circle cx="60" cy="60" r={r} fill="none" stroke="#eceae3" strokeWidth="11" />
      <circle
        cx="60" cy="60" r={r} fill="none" stroke={score == null ? "#d6d3cc" : color}
        strokeWidth="11" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off}
        transform="rotate(-90 60 60)"
      />
      <text x="60" y="58" textAnchor="middle" fontSize="30" fontWeight="800" fill={MARINO}>
        {score == null ? "—" : score}
      </text>
      <text x="60" y="76" textAnchor="middle" fontSize="11" fill="#6b7280">/ 100</text>
    </svg>
  );
}

export function BarsVentasGastos({ ventas, gastos }: { ventas: number[]; gastos: number[] }) {
  const w = 460, h = 190, pad = 28;
  const max = Math.max(1, ...ventas, ...gastos);
  const n = ventas.length;
  const gw = (w - pad * 2) / n;
  const y = (v: number) => h - pad - (v / max) * (h - pad * 2);
  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} role="img">
      <line x1={pad} y1={h - pad} x2={w - pad} y2={h - pad} stroke="#e7e5df" />
      {ventas.map((v, i) => {
        const bx = pad + i * gw;
        return (
          <g key={i}>
            <rect x={bx + gw * 0.18} y={y(v)} width={gw * 0.28} height={h - pad - y(v)} fill={AZUL} rx="3" />
            <rect x={bx + gw * 0.52} y={y(gastos[i])} width={gw * 0.28} height={h - pad - y(gastos[i])} fill={ROJO} rx="3" />
            <text x={bx + gw / 2} y={h - pad + 15} textAnchor="middle" fontSize="11" fill="#6b7280">
              Sem {i + 1}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

const DIAS = ["L", "M", "M", "J", "V", "S", "D"];

export function Heatmap({ matrix }: { matrix: number[][] }) {
  const max = Math.max(1, ...matrix.flat());
  const cell = 30, gap = 6, left = 44, top = 20;
  const color = (v: number) => {
    if (v <= 0) return "#f1efe9";
    const t = 0.2 + 0.8 * (v / max);
    return `rgba(42,75,168,${t.toFixed(2)})`;
  };
  return (
    <svg width="100%" viewBox={`0 0 ${left + 7 * (cell + gap)} ${top + 4 * (cell + gap) + 6}`}>
      {DIAS.map((d, i) => (
        <text key={i} x={left + i * (cell + gap) + cell / 2} y={top - 6} textAnchor="middle" fontSize="11" fill="#6b7280">{d}</text>
      ))}
      {matrix.map((fila, r) => (
        <g key={r}>
          <text x={0} y={top + r * (cell + gap) + cell / 2 + 4} fontSize="11" fill="#6b7280">S{r + 1}</text>
          {fila.map((v, c) => (
            <rect key={c} x={left + c * (cell + gap)} y={top + r * (cell + gap)} width={cell} height={cell} rx="6" fill={color(v)}>
              <title>{`S${r + 1} ${DIAS[c]}: S/ ${v}`}</title>
            </rect>
          ))}
        </g>
      ))}
    </svg>
  );
}

export function LineAhorroCuota({ ahorro, cuota }: { ahorro: number; cuota: number }) {
  const w = 460, h = 150, pad = 30;
  const max = Math.max(ahorro, cuota, 1) * 1.2;
  const y = (v: number) => h - pad - (v / max) * (h - pad * 2);
  const semanas = [0, 1, 2, 3];
  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`}>
      <line x1={pad} y1={h - pad} x2={w - pad} y2={h - pad} stroke="#e7e5df" />
      <line x1={pad} y1={y(cuota)} x2={w - pad} y2={y(cuota)} stroke={ROJO} strokeWidth="2" strokeDasharray="5 4" />
      <text x={w - pad} y={y(cuota) - 6} textAnchor="end" fontSize="11" fill={ROJO}>cuota semanal</text>
      <polyline
        points={semanas.map((s) => `${pad + (s / 3) * (w - pad * 2)},${y(ahorro)}`).join(" ")}
        fill="none" stroke={AZUL} strokeWidth="3"
      />
      <text x={pad} y={y(ahorro) - 8} fontSize="11" fill={AZUL}>ahorro posible</text>
    </svg>
  );
}
