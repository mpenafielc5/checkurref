import { FileText } from "lucide-react";
import Link from "next/link";
import { workHref } from "../sample-data";
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
            <Link
              href={workHref(work)}
              className="flex w-full flex-wrap items-center gap-x-5 gap-y-2 rounded-card border border-hairline bg-canvas px-5 py-3 hover:border-hairline-strong"
            >
              <FileText aria-hidden="true" className="size-6 text-body" />
              <span className="flex-1 font-semibold text-ink">{work.fileName}</span>
              <span className="text-small">{work.references} referencias</span>
              <WorkStatusChip work={work} />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
