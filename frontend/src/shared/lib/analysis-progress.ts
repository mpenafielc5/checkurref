/*
 * Avance en que empieza y termina la verificación, el mismo del backend
 * (PROGRESS_FIELDS y PROGRESS_VERIFIED en analysis_service.py): entre ambos
 * crece con cada referencia verificada.
 */
export const VERIFY_START = 30;
export const VERIFY_END = 95;

/**
 * Referencias verificadas, deducidas del avance. Es exacto hasta 65
 * referencias; con más, el backend informa cada pocas y el conteo nunca se
 * adelanta a lo real.
 */
export function verifiedCount(progress: number, total: number | null): number {
  if (!total) return 0;
  const done = Math.ceil(((progress - VERIFY_START) * total) / (VERIFY_END - VERIFY_START));
  return Math.min(Math.max(done, 0), total);
}
