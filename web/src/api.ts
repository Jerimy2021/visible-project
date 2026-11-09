import type { Ficha, ResumenPerfil } from "./types";

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "";

export async function getPerfiles(): Promise<ResumenPerfil[]> {
  const r = await fetch(`${BASE}/perfiles`);
  if (!r.ok) throw new Error(`perfiles ${r.status}`);
  const data = await r.json();
  return data.perfiles ?? [];
}

export async function getFicha(id: string): Promise<Ficha> {
  const r = await fetch(`${BASE}/perfiles/${id}`);
  if (!r.ok) throw new Error(`ficha ${r.status}`);
  return r.json();
}
