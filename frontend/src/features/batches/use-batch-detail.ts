import { useEffect, useState } from "react";
import { fetchBatchDetail, type BatchDetailOutcome } from "./api";
import { POLL_MS } from "./use-batch-upload";

export type BatchDetailState = { kind: "loading"; slow: boolean } | BatchDetailOutcome;

/**
 * El tablero del lote. Mientras algún trabajo se analiza, se vuelve a consultar;
 * si una consulta falla, se conserva lo que ya se ve y se reintenta.
 */
export function useBatchDetail(batchId: string, version = 0): BatchDetailState {
  const request = `${batchId}|${version}`;
  const [result, setResult] = useState<{ id: string; outcome: BatchDetailOutcome } | null>(null);
  const [slowId, setSlowId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const poll = async () => {
      const outcome = await fetchBatchDetail(batchId);
      if (!active) return;
      if (outcome.kind === "ready") setResult({ id: request, outcome });
      if (outcome.kind === "error" || outcome.batch.inProgress > 0) {
        timer = setTimeout(poll, POLL_MS);
      }
    };

    fetchBatchDetail(batchId, () => {
      if (active) setSlowId(request);
    }).then((outcome) => {
      if (!active) return;
      setResult({ id: request, outcome });
      if (outcome.kind === "ready" && outcome.batch.inProgress > 0) {
        timer = setTimeout(poll, POLL_MS);
      }
    });

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [batchId, request]);

  if (result?.id === request) return result.outcome;
  // Al volver a consultar (tras editar o eliminar) se sigue mostrando lo anterior.
  if (version > 0 && result?.id.startsWith(`${batchId}|`)) return result.outcome;
  return { kind: "loading", slow: slowId === request };
}
