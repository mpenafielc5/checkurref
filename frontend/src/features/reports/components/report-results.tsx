"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { Pagination } from "@/shared/components/ui/pagination";
import { PAGE_PARAM, paginate, parsePage } from "@/shared/lib/pagination";
import type { Verdict } from "@/shared/lib/verdicts";
import { filterByVerdict, parseVerdictFilter, VERDICT_PARAM } from "../rules";
import type { Report } from "../types";
import { ReferenceCard } from "./reference-card";
import { ReportSummary } from "./report-summary";

export const REFERENCES_PER_PAGE = 10;
const LIST_ID = "referencias";

/** Cómo se nombran las referencias mostradas, con o sin filtro. */
const FILTERED_NOUNS: Record<Verdict, string> = {
  verificada: "referencias verificadas",
  discrepancia: "referencias con discrepancias",
  contradiccion: "referencias con contradicción",
  sin_respaldo: "referencias sin respaldo",
  no_verificable: "referencias no verificables",
};

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
            noun={verdict ? FILTERED_NOUNS[verdict] : "referencias"}
            anchorId={LIST_ID}
          />
        ) : (
          <p className="text-small">Ninguna referencia tiene este veredicto.</p>
        )}
      </section>
    </>
  );
}
