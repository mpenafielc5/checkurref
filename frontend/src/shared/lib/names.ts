/** Una palabra con mayúscula inicial y el resto en minúsculas, según el español. */
export function capitalize(word: string): string {
  const lower = word.toLocaleLowerCase("es");
  return lower.charAt(0).toLocaleUpperCase("es") + lower.slice(1);
}

/**
 * Nombre completo con mayúscula inicial en cada palabra. Google suele
 * entregarlo todo en mayúsculas ("ANA TORRES VERA" pasa a "Ana Torres Vera").
 */
export function displayFullName(fullName: string): string {
  return fullName.trim().split(/\s+/).filter(Boolean).map(capitalize).join(" ");
}
