/** El backend gratuito se duerme sin uso: pasado este tiempo se avisa que está despertando. */
export const SLOW_UPLOAD_MS = 5_000;

/** Tiempo máximo de espera de la subida; el backend tarda hasta un minuto en despertar. */
export const UPLOAD_TIMEOUT_MS = 90_000;

/** Leer la sesión es local y casi inmediato; si tarda más, algo la bloqueó. */
export const SESSION_TIMEOUT_MS = 10_000;

/** Resuelve con el valor de la promesa, o con null si no llega a tiempo. */
export function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T | null> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => resolve(null), ms);
    promise.then(
      (value) => {
        clearTimeout(timer);
        resolve(value);
      },
      (error: unknown) => {
        clearTimeout(timer);
        reject(error);
      },
    );
  });
}

/** Lo que responde POST /analisis (AnalysisSubmittedResponse del backend). */
export type AnalysisSubmitted = {
  analysis_id: string;
  document_id: string;
  status: string;
  duplicate: boolean;
};

export type UploadOutcome =
  | { kind: "created"; analysisId: string }
  | { kind: "duplicate"; analysisId: string; finished: boolean }
  | { kind: "error"; message: string };

const GENERIC_ERROR = "No se pudo subir el archivo. Intenta de nuevo en unos minutos.";

/** Mensaje de error de FastAPI: un texto propio o la lista de validación automática. */
function detailOf(body: unknown): string | null {
  if (typeof body !== "object" || body === null || !("detail" in body)) return null;
  const { detail } = body;
  return typeof detail === "string" ? detail : null;
}

function isSubmitted(body: unknown): body is AnalysisSubmitted {
  return (
    typeof body === "object" &&
    body !== null &&
    "analysis_id" in body &&
    typeof body.analysis_id === "string" &&
    "duplicate" in body &&
    typeof body.duplicate === "boolean"
  );
}

/** Traduce la respuesta de la API a lo que la pantalla debe hacer. */
export function interpretUploadResponse(status: number, body: unknown): UploadOutcome {
  if ((status === 200 || status === 202) && isSubmitted(body)) {
    return body.duplicate
      ? {
          kind: "duplicate",
          analysisId: body.analysis_id,
          finished: body.status === "completado",
        }
      : { kind: "created", analysisId: body.analysis_id };
  }
  if (status === 401) {
    return { kind: "error", message: "Tu sesión venció. Vuelve a ingresar para subir el trabajo." };
  }
  return { kind: "error", message: detailOf(body) ?? GENERIC_ERROR };
}

/** Pantalla a la que lleva un análisis: informe si terminó, progreso si sigue. */
export function analysisHref(analysisId: string, finished: boolean): string {
  return finished
    ? `/estudiante/trabajos/${analysisId}`
    : `/estudiante/trabajos/${analysisId}/progreso`;
}
