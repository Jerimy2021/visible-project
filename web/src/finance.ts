export const TEA = 0.45;

/** Cuota mensual, sistema francés, a partir de la TEA efectiva anual. */
export function cuotaFrancesa(principal: number, nMeses: number, tea = TEA): number {
  const i = Math.pow(1 + tea, 1 / 12) - 1;
  return (principal * i) / (1 - Math.pow(1 + i, -nMeses));
}

export const soles = (n: number) =>
  `S/ ${n.toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const pct = (n: number) => `${n.toFixed(1)}%`;
