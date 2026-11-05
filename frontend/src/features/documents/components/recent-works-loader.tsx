"use client";

import { useHistory } from "../use-history";
import { RecentWorks } from "./recent-works";

/** Cuántos trabajos muestra el inicio; el resto está en Mis trabajos. */
const RECENT_COUNT = 3;

/**
 * Análisis recientes del estudiante con datos reales (HU-07). Es un atajo del
 * inicio: mientras carga, si falla o si aún no hay trabajos, no ocupa lugar.
 */
export function RecentWorksLoader() {
  const state = useHistory(1, "");
  if (state.kind !== "ready" || state.page.items.length === 0) return null;
  return <RecentWorks works={state.page.items.slice(0, RECENT_COUNT)} />;
}
