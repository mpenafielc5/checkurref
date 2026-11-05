import { useCallback, useEffect, useState } from "react";
import { createSupabaseBrowserClient } from "@/shared/lib/supabase/client";
import { fetchAnalysis, type AnalysisOutcome } from "./api";
import { isFinished, mergeSnapshot, snapshotFromRow, type AnalysisSnapshot } from "./progress";

export type ProgressState = { kind: "loading"; slow: boolean } | AnalysisOutcome;

/** Consulta de respaldo por si Realtime se corta; Realtime avisa al instante. */
export const POLL_MS = 10_000;

/** Cada suscripción tiene su canal: uno que se está cerrando no se reutiliza. */
let channelCount = 0;

type Result = { analysisId: string; outcome: AnalysisOutcome };

/**
 * Estado en vivo de un análisis (HU-05): primero lo pide a la API y luego
 * escucha los cambios de su fila en analisis con Supabase Realtime. Al quedar
 * suscrito lo vuelve a pedir, por si cambió entre ambos pasos. Mientras no
 * termina, también lo consulta cada 10 s.
 */
export function useAnalysisProgress(analysisId: string): ProgressState {
  const [result, setResult] = useState<Result | null>(null);
  const [slowId, setSlowId] = useState<string | null>(null);

  /** Un estado nuevo nunca hace retroceder la pantalla ni borra lo que ya se ve. */
  const applyOutcome = useCallback(
    (outcome: AnalysisOutcome) => {
      setResult((previous) => {
        const current = previous?.analysisId === analysisId ? previous.outcome : null;
        if (current?.kind !== "ready") return { analysisId, outcome };
        if (outcome.kind !== "ready") return previous;
        const analysis = mergeSnapshot(current.analysis, outcome.analysis);
        return analysis === current.analysis
          ? previous
          : { analysisId, outcome: { kind: "ready", analysis } };
      });
    },
    [analysisId],
  );

  const applySnapshot = useCallback(
    (snapshot: AnalysisSnapshot) => {
      setResult((previous) => {
        if (previous?.analysisId !== analysisId || previous.outcome.kind !== "ready") {
          return previous;
        }
        const analysis = mergeSnapshot(previous.outcome.analysis, snapshot);
        return analysis === previous.outcome.analysis
          ? previous
          : { analysisId, outcome: { kind: "ready", analysis } };
      });
    },
    [analysisId],
  );

  useEffect(() => {
    let active = true;
    const refresh = (onSlow: () => void = () => undefined) => {
      fetchAnalysis(analysisId, onSlow).then((outcome) => {
        if (active) applyOutcome(outcome);
      });
    };
    refresh(() => {
      if (active) setSlowId(analysisId);
    });

    channelCount += 1;
    const supabase = createSupabaseBrowserClient();
    const channel = supabase
      .channel(`progreso-${analysisId}-${channelCount}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "analisis",
          filter: `id=eq.${analysisId}`,
        },
        (payload) => {
          const snapshot = snapshotFromRow(payload.new);
          if (active && snapshot) applySnapshot(snapshot);
        },
      )
      .subscribe((status) => {
        if (status === "SUBSCRIBED") refresh();
      });

    return () => {
      active = false;
      void supabase.removeChannel(channel);
    };
  }, [analysisId, applyOutcome, applySnapshot]);

  const outcome = result?.analysisId === analysisId ? result.outcome : null;
  const finished = outcome?.kind === "ready" && isFinished(outcome.analysis.status);

  useEffect(() => {
    if (finished) return;
    let active = true;
    const timer = setInterval(() => {
      fetchAnalysis(analysisId, () => undefined).then((polled) => {
        if (active) applyOutcome(polled);
      });
    }, POLL_MS);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [analysisId, finished, applyOutcome]);

  return outcome ?? { kind: "loading", slow: slowId === analysisId };
}
