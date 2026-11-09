export type Estado = "Apta" | "En proceso" | "Faltan datos";

export interface ResumenPerfil {
  id: string;
  telefono_mascara: string;
  nombre: string;
  rubro: string;
  zona: string;
  puntaje: number | null;
  estado: Estado;
  ventas_semana_promedio: number;
  tendencia_pct?: number;
  semanas_con_datos?: number;
}

export interface Decision {
  monto: number;
  cuota: number;
  plazo_meses: number;
  tea: number;
  ratio_cuota_excedente: number | null;
}

export interface Evaluacion {
  estado: Estado;
  puntaje: number | null;
  semanas_con_datos: number;
  ventas_semana_promedio: number;
  tendencia_pct: number;
  estabilidad: string;
  coef_variacion_pct: number;
  constancia: number;
  coincidencia_yape_pct: number | null;
  ventas_por_semana: number[];
  gastos_por_semana: number[];
  heatmap: number[][];
  subpuntajes: Record<string, number>;
  pesos: Record<string, number>;
  decision: Decision;
  base_semanal: number;
  base_mensual: number;
  dias_con_registro: number;
}

export interface Movimiento {
  fecha: string;
  monto: number;
  concepto: string;
  categoria: string;
  subcategoria: string;
  por_cobrar: boolean;
  origen: string;
  confianza: number | null;
  foto_url: string | null;
}

export interface Totales {
  ventas: number;
  gastos_negocio: number;
  gastos_personales: number;
  cuotas_deuda: number;
  ganancia: number;
  ahorro: number;
  por_cobrar: number;
  por_clasificar: number;
}

export interface ResumenEmprendedora {
  desde: string;
  hasta: string;
  semana: Totales;
  variacion_ganancia_pct: number | null;
  por_dia: { fecha: string; letra: string; ganancia: number }[];
  mes: Totales;
  subcategorias_mes: Record<string, Record<string, number>>;
  dias_con_registro_7: number;
}

export interface Ficha {
  id: string;
  telefono_mascara: string;
  nombre: string;
  rubro: string;
  zona: string;
  consentimiento: string;
  evaluacion: Evaluacion;
  emprendedora?: ResumenEmprendedora;
  movimientos: Movimiento[];
}
