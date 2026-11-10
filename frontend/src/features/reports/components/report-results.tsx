"use client";

import { ListFilter } from "lucide-react";
import { usePathname, useSearchParams } from "next/navigation";
import { EmptyState } from "@/shared/components/ui/empty-state";
import { Pagination } from "@/shared/components/ui/pagination";
import { PAGE_PARAM, paginate, parsePage } from "@/shared/lib/pagination";
import type { Verdict } from "@/shared/lib/verdicts";
import { filterByVerdict, parseVerdictFilter, VERDICT_PARAM } from "../rules";
import type { Report } from "../types";
import { ReferenceCard } from "./reference-card";
import { ReportSummary } from "./report-summary";

export const REFERENCES_PER_PAGE = 10;
const LIST_ID = "referencias";

/** Cómo se nombran las referencias mostradas, con o sin filtro: [una, varias]. */
const FILTERED_NOUNS: Record<Verdict, [string, string]> = {
  verificada: ["referencia verificada", "referencias verificadas"],
  discrepancia: ["referencia con discrepancias", "referencias con discrepancias"],
  contradiccion: ["referencia con contradicción", "referencias con contradicción"],
  sin_respaldo: ["referencia sin respaldo", "referencias sin respaldo"],
  no_verificable: ["referencia no verificable", "referencias no verificables"],
};
const ALL_NOUNS: [string, string] = ["referencia", "referencias"];

/**
 * Resumen y referencias del informe. El filtro por veredicto se aplica antes
 * de paginar (de 10 en 10), y ambos quedan en la dirección para volver a ellos.
 */
export function ReportResults({ report }: { report: Report }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const verdict = parseVerdictFilter(searchParams.get(VERDICT_PARAM));
  const slice = paginate(
    filterByVerdict(report.references, verdict),
    parsePage(searchParams.get(PAGE_PARAM)),
    REFERENCES_PER_PAGE,
  );

  /** Al cambiar de filtro se vuelve a la página 1. */
  function filterHref(target: Verdict | null): string {
    const params = new URLSearchParams(searchParams.toString());
    params.delete(PAGE_PARAM);
    if (target) params.set(VERDICT_PARAM, target);
    else params.delete(VERDICT_PARAM);
    const query = params.toString();
    return query ? `${pathname}?${query}` : pathname;
  }

  return (
    <>
      <ReportSummary
        index={report.index}
        counts={report.counts}
        queryErrors={report.queryErrors}
        active={verdict}
        filterHref={filterHref}
      />

      <section id={LIST_ID} aria-label="Referencias" className="flex scroll-mt-6 flex-col gap-4">
        {slice.items.map((reference) => (
          <ReferenceCard key={reference.order} reference={reference} />
        ))}
        {slice.total > 0 ? (
          <Pagination
            slice={slice}
            pathname={pathname}
            query={searchParams.toString()}
            nounOne={(verdict ? FILTERED_NOUNS[verdict] : ALL_NOUNS)[0]}
            noun={(verdict ? FILTERED_NOUNS[verdict] : ALL_NOUNS)[1]}
            anchorId={LIST_ID}
          />
        ) : (
          <EmptyState
            icon={ListFilter}
            title="Sin referencias con este veredicto"
            description="Elige otro veredicto en la barra de arriba o pulsa Todas."
          />
        )}
      </section>
    </>
  );
}
