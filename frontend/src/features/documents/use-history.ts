import { useEffect, useState } from "react";
import { fetchHistory, type HistoryOutcome } from "./api";

export type HistoryState = { kind: "loading"; slow: boolean } | HistoryOutcome;

/**
 * Una página del historial (HU-07). Cada página y búsqueda es una petición
 * distinta: mientras no llega la respuesta de la actual, el estado es "loading"
 * (con slow si el backend está despertando).
 */
export function useHistory(page: number, search: string): HistoryState {
  const request = `${page}|${search}`;
  const [result, setResult] = useState<{ request: string; outcome: HistoryOutcome } | null>(null);
  const [slowRequest, setSlowRequest] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetchHistory(page, search, () => {
      if (active) setSlowRequest(request);
    }).then((outcome) => {
      if (active) setResult({ request, outcome });
    });
    return () => {
      active = false;
    };
  }, [page, search, request]);

  if (result?.request === request) return result.outcome;
  return { kind: "loading", slow: slowRequest === request };
}
