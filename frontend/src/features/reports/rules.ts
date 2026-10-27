import { VERDICT_ORDER, type Verdict } from "@/shared/lib/verdicts";
import type { ReferenceResult } from "./types";

/** El filtro por veredicto viaja en la dirección, como la página (?veredicto=discrepancia). */
export const VERDICT_PARAM = "veredicto";

/** Lee el veredicto de la dirección; cualquier valor desconocido es "sin filtro". */
export function parseVerdictFilter(raw: string | null | undefined): Verdict | null {
  return VERDICT_ORDER.find((verdict) => verdict === raw) ?? null;
}

/** Referencias del veredicto pedido, en su orden original; sin filtro, todas. */
export function filterByVerdict(
  references: ReferenceResult[],
  verdict: Verdict | null,
): ReferenceResult[] {
  return verdict ? references.filter((reference) => reference.verdict === verdict) : references;
}

/**
 * La tarjeta empieza cerrada solo si no hay nada que corregir: verificada y sin
 * hallazgos de formato. Las demás se muestran abiertas.
 */
export function startsCollapsed(reference: ReferenceResult): boolean {
  return reference.verdict === "verificada" && reference.formatFindings.length === 0;
}

/** Texto plano de la referencia, para mostrarla en una línea cuando está contraída. */
export function referenceText(reference: ReferenceResult): string {
  return reference.segments.map((segment) => segment.text).join("");
}
