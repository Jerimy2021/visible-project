export const TEA = 0.45;

/** Cuota mensual, sistema francés, a partir de la TEA efectiva anual. */
export function cuotaFrancesa(principal: number, nMeses: number, tea = TEA): number {
  const i = Math.pow(1 + tea, 1 / 12) - 1;
  return (principal * i) / (1 - Math.pow(1 + i, -nMeses));
}

/** Monto con espacio como separador de miles: "S/ 82 400", "S/ 148.39". */
export const soles = (n: number) => {
  const neg = n < 0;
  const x = Math.abs(n);
  const entero = Math.floor(x);
  const dec = Math.round((x - entero) * 100);
  const miles = entero.toLocaleString("en-US").replace(/,/g, " ");
  const cuerpo = dec > 0 ? `${miles}.${String(dec).padStart(2, "0")}` : miles;
  return `${neg ? "-" : ""}S/ ${cuerpo}`;
};

export const pct = (n: number) => `${n.toFixed(1)}%`;
