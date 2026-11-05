/** Nombre que ve el usuario de la norma detectada por el análisis (APA, IEEE o MIXTA). */
const STANDARD_LABELS: Record<string, string> = {
  APA: "APA",
  IEEE: "IEEE",
  MIXTA: "APA e IEEE",
};

/** null si aún no se detecta o si no se pudo identificar (DESCONOCIDA). */
export function standardLabel(norm: string | null): string | null {
  return (norm !== null && STANDARD_LABELS[norm]) || null;
}
