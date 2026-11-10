/** Pantalla a la que lleva un análisis: informe si terminó, progreso si sigue. */
export function analysisHref(analysisId: string, finished: boolean): string {
  return finished
    ? `/estudiante/trabajos/${analysisId}`
    : `/estudiante/trabajos/${analysisId}/progreso`;
}
