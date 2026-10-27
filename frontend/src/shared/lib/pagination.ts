/** Paginación de listas: la página actual viaja en la dirección (?pagina=2). */

export const PAGE_PARAM = "pagina";

export type PageSlice<T> = {
  items: T[];
  page: number;
  totalPages: number;
  total: number;
  /** Posición (desde 1) del primer y el último elemento mostrados; 0 si no hay. */
  first: number;
  last: number;
};

/** Lee el número de página de la dirección; cualquier valor inválido es la 1. */
export function parsePage(raw: string | null | undefined): number {
  const page = Number(raw);
  return Number.isInteger(page) && page >= 1 ? page : 1;
}

/**
 * Dirección de una página que conserva los demás parámetros (por ejemplo, un
 * filtro). hash lleva al inicio de la lista en lugar del tope de la pantalla.
 */
export function pageHref(pathname: string, query: string, page: number, hash = ""): string {
  const params = new URLSearchParams(query);
  params.set(PAGE_PARAM, String(page));
  return `${pathname}?${params.toString()}${hash ? `#${hash}` : ""}`;
}

/** Devuelve la página pedida; si se pasa del final, la última. */
export function paginate<T>(items: T[], page: number, pageSize: number): PageSlice<T> {
  const total = items.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const current = Math.min(Math.max(1, page), totalPages);
  const start = (current - 1) * pageSize;
  const pageItems = items.slice(start, start + pageSize);

  return {
    items: pageItems,
    page: current,
    totalPages,
    total,
    first: pageItems.length > 0 ? start + 1 : 0,
    last: start + pageItems.length,
  };
}
