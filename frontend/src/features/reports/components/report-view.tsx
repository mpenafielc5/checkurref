import { buttonStyles } from "@/shared/components/ui/button-styles";
import { StatusChip } from "@/shared/components/ui/status-chip";
import type { Report } from "../types";
import { ReportResults } from "./report-results";

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

      <ReportResults report={report} />
    </div>
  );
}
