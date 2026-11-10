import { getApiUrl } from "@/shared/lib/env";
import { createSupabaseBrowserClient } from "@/shared/lib/supabase/client";

/** Leer la sesión es local y casi inmediato; si tarda más, algo la bloqueó. */
export const SESSION_TIMEOUT_MS = 10_000;

/** El backend gratuito se duerme sin uso: pasado este tiempo se avisa que está despertando. */
export const SLOW_RESPONSE_MS = 5_000;

/** Tiempo máximo de una consulta; el backend tarda hasta un minuto en despertar. */
export const REQUEST_TIMEOUT_MS = 90_000;

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

/** Respuesta de la API: el código HTTP y el cuerpo JSON (null si no hay). */
export type ApiResponse = { kind: "response"; status: number; body: unknown };

/** Sin sesión, sin conexión o sin respuesta a tiempo: no hubo respuesta de la API. */
export type ApiFailure = { kind: "failed"; reason: "session" | "network" };

/**
 * Petición a la API con el token de la sesión. Si tarda más de 5 s avisa con
 * onSlow: el backend gratuito puede estar despertando. Los temporizadores cubren
 * también la lectura de la sesión, que en el navegador a veces no responde.
 */
async function apiRequest(
  path: string,
  init: { method?: string; headers?: Record<string, string>; body?: string },
  onSlow: () => void,
): Promise<ApiResponse | ApiFailure> {
  const controller = new AbortController();
  const slowTimer = setTimeout(onSlow, SLOW_RESPONSE_MS);
  const abortTimer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const session = await withTimeout(
      createSupabaseBrowserClient().auth.getSession(),
      SESSION_TIMEOUT_MS,
    );
    const token = session?.data.session?.access_token;
    if (!token) return { kind: "failed", reason: "session" };

    const response = await fetch(`${getApiUrl()}${path}`, {
      ...init,
      headers: { ...init.headers, Authorization: `Bearer ${token}` },
      signal: controller.signal,
    });
    const body: unknown = await response.json().catch(() => null);
    return { kind: "response", status: response.status, body };
  } catch {
    return { kind: "failed", reason: "network" };
  } finally {
    clearTimeout(slowTimer);
    clearTimeout(abortTimer);
  }
}

export function apiGet(
  path: string,
  onSlow: () => void = () => undefined,
): Promise<ApiResponse | ApiFailure> {
  return apiRequest(path, {}, onSlow);
}

export function apiPost(
  path: string,
  payload: unknown,
  onSlow: () => void = () => undefined,
): Promise<ApiResponse | ApiFailure> {
  return apiRequest(
    path,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    onSlow,
  );
}

/** Despierta al backend antes de una subida; si no responde, no pasa nada. */
export function wakeApi(): void {
  fetch(`${getApiUrl()}/health`).catch(() => undefined);
}
