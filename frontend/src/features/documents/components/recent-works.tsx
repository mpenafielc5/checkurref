import { FileText } from "lucide-react";
import Link from "next/link";
import { Skeleton, SkeletonText } from "@/shared/components/ui/skeleton";
import { workHref } from "../history";
import type { Work } from "../types";
import { WorkStatusChip } from "./work-status-chip";

/** Análisis recientes del estudiante (maqueta 10). Cada fila es clicable. */
export function RecentWorks({ works }: { works: Work[] }) {
  return (
    <section aria-labelledby="titulo-recientes" className="flex flex-col gap-3">
      <h2 id="titulo-recientes" className="text-small font-semibold tracking-normal text-ink">
        Análisis recientes
      </h2>
      <ul className="flex flex-col gap-2">
        {works.map((work) => (
          <li key={work.analysisId} className="flex">
            {/* Misma forma en todas las filas: en el celular, el nombre arriba y los datos
                debajo; desde md, todo en una línea. Un nombre largo se corta con "…". */}
            <Link
              href={workHref(work)}
              className="flex w-full items-center gap-4 rounded-card border border-hairline bg-canvas px-5 py-3 hover:border-hairline-strong"
            >
              <FileText aria-hidden="true" className="size-6 shrink-0 text-body" />
              <span className="flex min-w-0 flex-1 flex-col gap-1 md:flex-row md:items-center md:gap-5">
                <span className="truncate font-semibold text-ink md:flex-1" title={work.fileName}>
                  {work.fileName}
                </span>
                <span className="flex shrink-0 items-center gap-3">
                  <span className="text-small">
                    {work.references} {work.references === 1 ? "referencia" : "referencias"}
                  </span>
                  <WorkStatusChip work={work} />
                </span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Esqueleto de los análisis recientes, con la forma de su título y sus filas. */
export function RecentWorksSkeleton({ rows }: { rows: number }) {
  return (
    <div className="flex flex-col gap-3">
      <SkeletonText textClass="text-small" widthClass="w-36" />
      <div className="flex flex-col gap-2">
        {Array.from({ length: rows }, (_, index) => (
          <Skeleton key={index} className="h-14 w-full rounded-card" />
        ))}
      </div>
    </div>
  );
}
