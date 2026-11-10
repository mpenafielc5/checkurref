import type { ReactNode } from "react";
import { Skeleton, SkeletonText } from "./skeleton";

/*
 * Tabla de datos con el estilo de las maquetas: encabezado con fondo crema y
 * líneas finas. Las tablas largas se cambian en el celular por una lista de
 * tarjetas (cardsOnMobile); las cortas se desplazan horizontalmente.
 */

type DataTableProps = {
  caption: string;
  /** La pantalla muestra tarjetas en el celular: la tabla aparece desde md. */
  cardsOnMobile?: boolean;
  /** Tarjetas también en la tableta: la tabla aparece desde lg. */
  cardsOnTablet?: boolean;
  children: ReactNode;
};

export function DataTable({
  caption,
  cardsOnMobile = false,
  cardsOnTablet = false,
  children,
}: DataTableProps) {
  const visibility = cardsOnTablet ? "hidden lg:flex" : cardsOnMobile ? "hidden md:flex" : "flex";
  return (
    <div className={`${visibility} w-full overflow-x-auto rounded-card border border-hairline`}>
      <table className="w-full min-w-xl border-collapse text-small">
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </div>
  );
}

export const tableHeadClass = "bg-canvas text-left text-caption font-semibold text-body";
export const thClass = "px-4 py-2 font-semibold";
export const tdClass = "border-t border-hairline px-4 py-2 text-ink";
export const numericClass = "text-right tabular-nums";

/** Lista de tarjetas que reemplaza a la tabla en el celular. */
export const cardListClass = "flex flex-col gap-2 md:hidden";
/** Igual, pero también en la tableta: para tablas con botones que no caben en ese ancho. */
export const tabletCardListClass = "flex flex-col gap-2 lg:hidden";
export const cardClass =
  "flex w-full flex-col gap-2 rounded-card border border-hairline bg-canvas px-4 py-3";

type DataTableSkeletonProps = {
  columns: number;
  rows: number;
  /** La última columna lleva un botón (las filas son más altas). */
  withAction?: boolean;
  /** Igual que en DataTable: tarjetas en el celular y tabla desde md. */
  cardsOnMobile?: boolean;
  /** Igual que en DataTable: tarjetas hasta la tableta y tabla desde lg. */
  cardsOnTablet?: boolean;
};

/** Esqueleto de DataTable con el mismo encabezado, relleno y líneas. */
export function DataTableSkeleton({
  columns,
  rows,
  withAction = false,
  cardsOnMobile = false,
  cardsOnTablet = false,
}: DataTableSkeletonProps) {
  const withCards = cardsOnMobile || cardsOnTablet;
  const tableVisibility = cardsOnTablet
    ? "hidden lg:flex"
    : cardsOnMobile
      ? "hidden md:flex"
      : "flex";
  const cells = Array.from({ length: columns }, (_, index) => index);
  const rowIndexes = Array.from({ length: rows }, (_, index) => index);

  return (
    <>
      {withCards ? (
        <div className={cardsOnTablet ? tabletCardListClass : cardListClass}>
          {rowIndexes.map((row) => (
            <div key={row} className={cardClass}>
              <SkeletonText widthClass="w-48 max-w-full" />
              <SkeletonText textClass="text-small" widthClass="w-32 max-w-full" />
              {withAction ? <Skeleton className="h-control w-full rounded-pill" /> : null}
            </div>
          ))}
        </div>
      ) : null}
      <div
        className={`${tableVisibility} w-full flex-col overflow-hidden rounded-card border border-hairline`}
      >
        <div className="flex gap-4 bg-canvas px-4 py-2">
          {cells.map((cell) => (
            <span key={cell} className="flex flex-1 flex-col">
              <SkeletonText textClass="text-caption" widthClass="w-1/2" />
            </span>
          ))}
        </div>
        {rowIndexes.map((row) => (
          <div key={row} className="flex items-center gap-4 border-t border-hairline px-4 py-2">
            {cells.map((cell) => (
              <span key={cell} className="flex flex-1 flex-col">
                {withAction && cell === columns - 1 ? (
                  <Skeleton className="h-control w-28 max-w-full rounded-pill" />
                ) : (
                  <SkeletonText textClass="text-small" widthClass="w-3/4" />
                )}
              </span>
            ))}
          </div>
        ))}
      </div>
    </>
  );
}
