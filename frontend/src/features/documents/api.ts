import { apiGet } from "@/shared/lib/api-client";
import { getApiUrl } from "@/shared/lib/env";
import type { PageSlice } from "@/shared/lib/pagination";
import { createSupabaseBrowserClient } from "@/shared/lib/supabase/client";
import { isHistoryDto, toWorkPage } from "./history";
import type { Work } from "./types";
import {
  interpretUploadResponse,
  SESSION_TIMEOUT_MS,
  SLOW_UPLOAD_MS,
  UPLOAD_TIMEOUT_MS,
  withTimeout,
  type UploadOutcome,
} from "./upload-rules";

/**
 * Sube el PDF a la API con el token de la sesión (HU-04). La norma (APA o
 * IEEE) no se pregunta: la detecta el análisis. Si tarda más de 5 s avisa con
 * onSlow: el backend gratuito puede estar despertando.
 *
 * Los temporizadores cubren todo el proceso, incluida la lectura de la sesión:
 * en el navegador, getSession de Supabase a veces no responde, y la pantalla no
 * debe quedarse en "Subiendo…" sin explicación.
 */
export async function submitDocument(file: File, onSlow: () => void): Promise<UploadOutcome> {
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
    const response = await fetch(`${getApiUrl()}/analisis`, {
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

/** Despierta al backend antes de la subida; si no responde, no pasa nada. */
export function wakeApi(): void {
  fetch(`${getApiUrl()}/health`).catch(() => undefined);
}

export type HistoryOutcome =
  { kind: "ready"; page: PageSlice<Work> } | { kind: "error"; message: string };

/** Una página del historial del estudiante (HU-07), con la búsqueda por nombre. */
export async function fetchHistory(
  page: number,
  search: string,
  onSlow: () => void,
): Promise<HistoryOutcome> {
  const params = new URLSearchParams({ pagina: String(page) });
  if (search) params.set("buscar", search);
  const response = await apiGet(`/analisis?${params.toString()}`, onSlow);
  if (response.kind === "response" && response.status === 200 && isHistoryDto(response.body)) {
    return { kind: "ready", page: toWorkPage(response.body) };
  }
  return {
    kind: "error",
    message:
      response.kind === "failed" && response.reason === "session"
        ? "No se pudo verificar tu sesión. Recarga la página e intenta de nuevo."
        : "No se pudo cargar la lista de tus trabajos. Intenta de nuevo en unos minutos.",
  };
}
