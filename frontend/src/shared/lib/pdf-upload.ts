import { SESSION_TIMEOUT_MS, withTimeout } from "@/shared/lib/api-client";
import { getApiUrl } from "@/shared/lib/env";
import { createSupabaseBrowserClient } from "@/shared/lib/supabase/client";

/** El backend gratuito se duerme sin uso: pasado este tiempo se avisa que está despertando. */
export const SLOW_UPLOAD_MS = 5_000;

/** Tiempo máximo de espera de la subida; el backend tarda hasta un minuto en despertar. */
export const UPLOAD_TIMEOUT_MS = 90_000;

/** Lo que responde la API al recibir un PDF (AnalysisSubmittedResponse del backend). */
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
export function detailOf(body: unknown): string | null {
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

/**
 * Sube un PDF a la API con el token de la sesión: la misma función para el
 * estudiante (HU-04) y para el lote del docente (HU-08 CA04). Si tarda más de 5 s
 * avisa con onSlow: el backend gratuito puede estar despertando.
 *
 * Los temporizadores cubren todo el proceso, incluida la lectura de la sesión:
 * en el navegador, getSession de Supabase a veces no responde, y la pantalla no
 * debe quedarse en "Subiendo…" sin explicación.
 */
export async function uploadPdf(
  path: string,
  file: File,
  onSlow: () => void,
): Promise<UploadOutcome> {
  const controller = new AbortController();
  const slowTimer = setTimeout(onSlow, SLOW_UPLOAD_MS);
  const abortTimer = setTimeout(() => controller.abort(), UPLOAD_TIMEOUT_MS);
  try {
    const session = await withTimeout(
      createSupabaseBrowserClient().auth.getSession(),
      SESSION_TIMEOUT_MS,
    );
    if (!session) {
      return {
        kind: "error",
        message: "No se pudo verificar tu sesión. Recarga la página e intenta de nuevo.",
      };
    }
    const token = session.data.session?.access_token;
    if (!token) return interpretUploadResponse(401, null);

    const form = new FormData();
    form.append("archivo", file);
    const response = await fetch(`${getApiUrl()}${path}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: form,
      signal: controller.signal,
    });
    const body: unknown = await response.json().catch(() => null);
    return interpretUploadResponse(response.status, body);
  } catch {
    return {
      kind: "error",
      message:
        "No se pudo conectar con el motor de análisis. Revisa tu conexión e intenta de nuevo.",
    };
  } finally {
    clearTimeout(slowTimer);
    clearTimeout(abortTimer);
  }
}
