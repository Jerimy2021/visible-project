import type { Centro, ExtintorRow, Ficha, NoCumple, Observacion } from "./types";

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "";
const KEY = (import.meta.env.VITE_API_KEY as string | undefined) ?? "";

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { headers: { "x-api-key": KEY } });
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json();
}

export const getCentro = (site: string, periodo: string) =>
  get<Centro>(`/centro?site=${encodeURIComponent(site)}&periodo=${periodo}`);

export const getExtintores = (site: string, estado: string) =>
  get<{ extintores: ExtintorRow[] }>(
    `/extintores?site=${encodeURIComponent(site)}${estado ? `&estado=${encodeURIComponent(estado)}` : ""}`,
  ).then((d) => d.extintores);

export const getExtintor = (codigo: string) => get<Ficha>(`/extintor/${encodeURIComponent(codigo)}`);

export const getObservaciones = (site: string, periodo: string) =>
  get<{ observaciones: Observacion[] }>(
    `/observaciones?site=${encodeURIComponent(site)}&periodo=${periodo}`,
  ).then((d) => d.observaciones);

export const getNoCumplieron = (site: string, periodo: string) =>
  get<{ no_cumplieron: NoCumple[] }>(
    `/no-cumplieron?site=${encodeURIComponent(site)}&periodo=${periodo}`,
  ).then((d) => d.no_cumplieron);

/** Pide URL prefirmada, sube el CSV a S3 y devuelve la key (la Lambda procesa al subir). */
export async function subirCsv(archivo: string, contenido: Blob): Promise<string> {
  const r = await fetch(`${BASE}/import/url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ archivo }),
  });
  if (!r.ok) throw new Error(`import/url → ${r.status}`);
  const { url, key } = await r.json();
  const put = await fetch(url, { method: "PUT", headers: { "Content-Type": "text/csv" }, body: contenido });
  if (!put.ok) throw new Error(`PUT S3 → ${put.status}`);
  return key;
}
