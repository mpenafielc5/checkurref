import { ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";
import { pageHref, type PageSlice } from "@/shared/lib/pagination";

const STEP_CLASSES = "inline-flex items-center gap-1 rounded-pill px-3 py-1.5 font-semibold";

type PaginationProps = {
  slice: Pick<PageSlice<unknown>, "page" | "totalPages" | "total" | "first" | "last">;
  /** Ruta de la pantalla; cada página se abre en ruta?pagina=n. */
  pathname: string;
  /** Parámetros actuales de la dirección (filtros); se conservan al cambiar de página. */
  query?: string;
  /** Qué se cuenta, en plural: "referencias", "trabajos". */
  noun: string;
  /** id del inicio de la lista: al cambiar de página se vuelve ahí, no al tope de la pantalla. */
  anchorId?: string;
};

/** "Anterior · Página 2 de 6 · Siguiente" y "Mostrando 11–20 de 58". */
export function Pagination({ slice, pathname, query = "", noun, anchorId }: PaginationProps) {
  const { page, totalPages, total, first, last } = slice;
  const href = (target: number) => pageHref(pathname, query, target, anchorId);

  return (
    <nav
      aria-label={`Páginas de ${noun}`}
      className="flex w-full flex-col items-center gap-2 text-small md:flex-row md:justify-between"
    >
      <p>
        Mostrando {first}–{last} de {total} {noun}
      </p>
      {totalPages > 1 ? (
        <div className="flex items-center gap-2">
          {page > 1 ? (
            <Link
              href={href(page - 1)}
              className={`${STEP_CLASSES} text-ink hover:bg-hairline-soft`}
            >
              <ChevronLeft aria-hidden="true" className="size-4" />
              Anterior
            </Link>
          ) : (
            <span aria-disabled="true" className={`${STEP_CLASSES} text-muted-soft`}>
              <ChevronLeft aria-hidden="true" className="size-4" />
              Anterior
            </span>
          )}
          <span aria-current="page" className="text-ink">
            Página {page} de {totalPages}
          </span>
          {page < totalPages ? (
            <Link
              href={href(page + 1)}
              className={`${STEP_CLASSES} text-ink hover:bg-hairline-soft`}
            >
              Siguiente
              <ChevronRight aria-hidden="true" className="size-4" />
            </Link>
          ) : (
            <span aria-disabled="true" className={`${STEP_CLASSES} text-muted-soft`}>
              Siguiente
              <ChevronRight aria-hidden="true" className="size-4" />
            </span>
          )}
        </div>
      ) : null}
    </nav>
  );
}
