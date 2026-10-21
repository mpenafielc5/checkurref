import type { ReactNode } from "react";
import { Skeleton, SkeletonText } from "./skeleton";

/*
 * Tabla de datos con el estilo de las maquetas: encabezado con fondo crema y
 * líneas finas. En pantallas pequeñas se desplaza horizontalmente.
 */

export function DataTable({ caption, children }: { caption: string; children: ReactNode }) {
  return (
    <div className="flex w-full overflow-x-auto rounded-card border border-hairline">
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

type DataTableSkeletonProps = {
  columns: number;
  rows: number;
  /** La última columna lleva un botón (las filas son más altas). */
  withAction?: boolean;
};

/** Esqueleto de DataTable con el mismo encabezado, relleno y líneas. */
export function DataTableSkeleton({ columns, rows, withAction = false }: DataTableSkeletonProps) {
  const cells = Array.from({ length: columns }, (_, index) => index);

  return (
    <div className="flex w-full flex-col overflow-hidden rounded-card border border-hairline">
      <div className="flex gap-4 bg-canvas px-4 py-2">
        {cells.map((cell) => (
          <span key={cell} className="flex flex-1 flex-col">
            <SkeletonText textClass="text-caption" widthClass="w-1/2" />
          </span>
        ))}
      </div>
      {Array.from({ length: rows }, (_, row) => (
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
  );
}
