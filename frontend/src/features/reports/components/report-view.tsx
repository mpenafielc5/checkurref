import { buttonStyles } from "@/shared/components/ui/button-styles";
import { StatusChip } from "@/shared/components/ui/status-chip";
import type { Report } from "../types";
import { ReferenceCard } from "./reference-card";
import { ReportSummary } from "./report-summary";

/** Informe del documento: el diagnóstico de veracidad (maqueta 12). */
export function ReportView({ report }: { report: Report }) {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-title font-semibold tracking-normal text-ink">{report.fileName}</h2>
        <StatusChip tone="neutral">{report.standard}</StatusChip>
        <span className="flex-1" />
        <button type="button" disabled className={buttonStyles({ variant: "secondary" })}>
          Exportar PDF
        </button>
        <button type="button" disabled className={buttonStyles({ variant: "secondary" })}>
          Exportar CSV
        </button>
      </div>

      <ReportSummary index={report.index} counts={report.counts} />

      <section aria-label="Referencias" className="flex flex-col gap-4">
        {report.references.map((reference) => (
          <ReferenceCard key={reference.order} reference={reference} />
        ))}
      </section>
    </div>
  );
}
