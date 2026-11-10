import { useEffect, useState } from "react";
import { fetchBatches, type BatchesOutcome } from "./api";

export type BatchesState = { kind: "loading"; slow: boolean } | BatchesOutcome;

/** Una página de los lotes del docente; "loading" mientras no llega la respuesta de esa página. */
export function useBatches(page: number): BatchesState {
  const [result, setResult] = useState<{ page: number; outcome: BatchesOutcome } | null>(null);
  const [slowPage, setSlowPage] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    fetchBatches(page, () => {
      if (active) setSlowPage(page);
    }).then((outcome) => {
      if (active) setResult({ page, outcome });
    });
    return () => {
      active = false;
    };
  }, [page]);

  if (result?.page === page) return result.outcome;
  return { kind: "loading", slow: slowPage === page };
}
