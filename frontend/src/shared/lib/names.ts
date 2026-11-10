/** Una palabra con mayúscula inicial y el resto en minúsculas, según el español. */
export function capitalize(word: string): string {
  const lower = word.toLocaleLowerCase("es");
  return lower.charAt(0).toLocaleUpperCase("es") + lower.slice(1);
}

/** Partículas de los apellidos, que van en minúscula salvo al inicio del nombre. */
const PARTICLES = new Set(["de", "del", "la", "las", "los", "y", "e", "van", "von"]);

/**
 * Nombre completo con mayúscula inicial en cada palabra. Google y las portadas
 * suelen traerlo todo en mayúsculas ("ANA DE LA TORRE" pasa a "Ana de la Torre").
 */
export function displayFullName(fullName: string): string {
  return fullName
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((word, index) => {
      const lower = word.toLocaleLowerCase("es");
      return index > 0 && PARTICLES.has(lower) ? lower : capitalize(word);
    })
    .join(" ");
}
