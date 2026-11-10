import { apiDelete } from "./api-client";
import { detailOf } from "./pdf-upload";

export type DeleteWorkOutcome = { kind: "deleted" } | { kind: "error"; message: string };

const SESSION_ERROR = "No se pudo verificar tu sesión. Recarga la página e intenta de nuevo.";
const NETWORK_ERROR =
  "No se pudo conectar con el motor de análisis. Revisa tu conexión e intenta de nuevo.";
const GENERIC_ERROR = "No se pudo eliminar el trabajo. Intenta de nuevo en unos minutos.";

/** Traduce la respuesta de DELETE /analisis/{id} a lo que la pantalla debe hacer. */
export function interpretDeleteResponse(status: number, body: unknown): DeleteWorkOutcome {
  // 404: el trabajo ya no existe, que es justo lo que se quería.
  if (status === 204 || status === 404) return { kind: "deleted" };
  return { kind: "error", message: detailOf(body) ?? GENERIC_ERROR };
}

/**
 * Elimina un trabajo con su PDF y todos sus resultados. La usa el estudiante con
 * los suyos y el docente con los de sus lotes: la API comprueba que sea su dueño.
 */
export async function deleteWork(analysisId: string): Promise<DeleteWorkOutcome> {
  const response = await apiDelete(`/analisis/${encodeURIComponent(analysisId)}`);
  if (response.kind === "failed") {
    return {
      kind: "error",
      message: response.reason === "session" ? SESSION_ERROR : NETWORK_ERROR,
    };
  }
  return interpretDeleteResponse(response.status, response.body);
}
