/*
 * Progreso de un análisis (HU-05). El estado llega primero de GET
 * /analisis/{id} (AnalysisItem del backend) y luego en vivo con Supabase
 * Realtime, como fila de la tabla analisis. Aquí se traduce a las etapas de la
 * pantalla.
 */
import type { ProgressStep } from "./types";

/** Estado del análisis que cambia mientras corre. */
export type AnalysisSnapshot = {
  /** en_cola, extrayendo, segmentando, verificando, completado o error. */
  status: string;
  progress: number;
  totalReferences: number | null;
  /** APA, IEEE, MIXTA o DESCONOCIDA; null mientras no se detecta. */
  norm: string | null;
  errorMessage: string | null;
};

/** Un análisis abierto en la pantalla de progreso. */
export type AnalysisInfo = AnalysisSnapshot & {
  fileName: string;
  createdAt: string;
};

type AnalysisItemDto = {
  file_name: string;
  created_at: string;
  status: string;
  progress: number;
  total_references: number | null;
  norm: string | null;
  error_message: string | null;
};

/*
 * Avance en que empieza y termina la verificación, el mismo del backend
 * (PROGRESS_FIELDS y PROGRESS_VERIFIED en analysis_service.py): entre ambos
 * crece con cada referencia verificada.
 */
const VERIFY_START = 30;
const VERIFY_END = 95;

/** Orden de las etapas: un estado de una etapa anterior nunca reemplaza a uno posterior. */
const STATUS_RANK: Record<string, number> = {
  en_cola: 0,
  extrayendo: 1,
  segmentando: 2,
  verificando: 3,
  completado: 4,
  error: 4,
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}

function textOrNull(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

export function isAnalysisItemDto(body: unknown): body is AnalysisItemDto {
  return (
    isRecord(body) &&
    typeof body.file_name === "string" &&
    typeof body.created_at === "string" &&
    typeof body.status === "string" &&
    typeof body.progress === "number"
  );
}

export function toAnalysisInfo(dto: AnalysisItemDto): AnalysisInfo {
  return {
    fileName: dto.file_name,
    createdAt: dto.created_at,
    status: dto.status,
    progress: dto.progress,
    totalReferences: dto.total_references,
    norm: dto.norm,
    errorMessage: dto.error_message,
  };
}

/** Estado de una fila de analisis recibida por Realtime; null si no la reconoce. */
export function snapshotFromRow(row: unknown): AnalysisSnapshot | null {
  if (!isRecord(row) || typeof row.estado !== "string" || typeof row.progreso !== "number") {
    return null;
  }
  return {
    status: row.estado,
    progress: row.progreso,
    totalReferences: numberOrNull(row.total_referencias),
    norm: textOrNull(row.norma_detectada),
    errorMessage: textOrNull(row.mensaje_error),
  };
}

/**
 * Aplica un estado nuevo solo si no retrocede: Realtime y la consulta a la API
 * pueden llegar en cualquier orden.
 */
export function mergeSnapshot(current: AnalysisInfo, next: AnalysisSnapshot): AnalysisInfo {
  const currentRank = STATUS_RANK[current.status] ?? 0;
  const nextRank = STATUS_RANK[next.status] ?? 0;
  if (nextRank < currentRank) return current;
  if (nextRank === currentRank && next.progress < current.progress) return current;
  return { ...current, ...next };
}

export function isFinished(status: string): boolean {
  return status === "completado" || status === "error";
}

/** Avance de la verificación de 0 a 100. */
export function verifyPercent(progress: number): number {
  const ratio = (progress - VERIFY_START) / (VERIFY_END - VERIFY_START);
  return Math.round(Math.min(Math.max(ratio, 0), 1) * 100);
}

/**
 * Referencias verificadas, deducidas del avance. Es exacto hasta 65
 * referencias; con más, el backend informa cada pocas y el conteo nunca se
 * adelanta a lo real.
 */
export function verifiedCount(progress: number, total: number | null): number {
  if (!total) return 0;
  const done = Math.ceil(((progress - VERIFY_START) * total) / (VERIFY_END - VERIFY_START));
  return Math.min(Math.max(done, 0), total);
}

function countLabel(count: number, singular: string, plural: string): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

/** Etapa en curso: 1 texto, 2 referencias, 3 verificación; 5 si terminó. */
function currentStep(status: string): number {
  if (status === "segmentando") return 2;
  if (status === "verificando") return 3;
  if (status === "completado") return 5;
  return 1;
}

type StepText = { title: string; done: string; current?: string };

/** Las cinco etapas de la maqueta 11, con el detalle de la que está en curso. */
export function toSteps(analysis: AnalysisSnapshot): ProgressStep[] {
  const total = analysis.totalReferences ?? 0;
  const verified = verifiedCount(analysis.progress, analysis.totalReferences);
  const texts: StepText[] = [
    { title: "Subido", done: "Archivo PDF recibido" },
    {
      title: "Texto extraído",
      done: "Sección de referencias encontrada",
      current:
        analysis.status === "en_cola"
          ? "En cola; el análisis comenzará en breve"
          : "Buscando la sección de referencias",
    },
    {
      title:
        analysis.totalReferences === null
          ? "Referencias detectadas"
          : countLabel(total, "referencia detectada", "referencias detectadas"),
      done: "Campos separados con AnyStyle y formato revisado",
      current: "Separando los campos con AnyStyle",
    },
    {
      title: "Verificando con Crossref, OpenAlex y NLI",
      done: countLabel(total, "referencia verificada", "referencias verificadas"),
      current: `${verified} de ${countLabel(total, "referencia", "referencias")}`,
    },
    { title: "Informe listo", done: "Abriendo el informe…" },
  ];

  const current = currentStep(analysis.status);
  return texts.map((text, position) => {
    if (position < current) return { title: text.title, detail: text.done, state: "done" };
    if (position === current) {
      return { title: text.title, detail: text.current ?? "", state: "current" };
    }
    return { title: text.title, detail: "Pendiente", state: "pending" };
  });
}
