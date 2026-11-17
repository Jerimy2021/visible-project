export interface Aprobacion {
  estado?: string;
  aprobadas?: number;
  plantas?: number;
}
export interface Planta {
  site: string;
  nombre: string;
  total: number;
  inspeccionados: number;
  con_p: number;
  avance_pct: number;
  estado_aprobacion: string;
}
export interface Inspector {
  inspector: string;
  hechos: number;
  con_p: number;
  asignados: number;
}
export interface Punto {
  punto: string;
  p: number;
}
export interface TendenciaItem {
  periodo: string;
  avance_pct: number;
}
export interface Reincidente {
  codigo: string;
  meses: number;
}
export interface Pendiente {
  codigo: string;
  fecha_inspeccion: string;
  dias_abierto: number | null;
  puntos_p: string[];
}
export interface Centro {
  site: string;
  periodo: string;
  total: number;
  inspeccionados: number;
  faltan: number;
  avance_pct: number;
  p_abiertos: number;
  conformes_1a_pct: number | null;
  tiempo_levantamiento_dias: number | null;
  inspectores_activos: number;
  aprobacion: Aprobacion;
  por_planta: Planta[];
  por_inspector: Inspector[];
  punto_que_mas_falla: Punto[];
  tendencia: TendenciaItem[];
  reincidentes: Reincidente[];
  alertas: { pendientes: Pendiente[]; reincidentes: Reincidente[] };
}

export interface ExtintorRow {
  codigo: string;
  site: string;
  piso: string;
  ubicacion: string;
  zona_brigada: string;
  inspector_asignado: string;
  estado_inspeccion: string;
}
export interface Ficha {
  extintor: Record<string, unknown>;
  historial: Record<string, unknown>[];
}
