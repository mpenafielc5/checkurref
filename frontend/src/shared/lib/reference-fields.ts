/** Nombres que ve el usuario para los campos de una referencia; la API manda el código de la base. */
const FIELD_LABELS: Record<string, string> = {
  titulo: "Título",
  autores: "Autores",
  anio: "Año",
  doi: "DOI",
  contenedor: "Revista o libro",
  volumen: "Volumen",
  paginas: "Páginas",
  numero: "Número",
  editorial: "Editorial",
};

export function fieldLabel(field: string): string {
  return FIELD_LABELS[field] ?? field;
}
