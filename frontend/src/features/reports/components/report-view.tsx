import { StatusChip } from "@/shared/components/ui/status-chip";
import type { Report } from "../types";
import { PrintButton } from "./print-button";
import { PrintableReport } from "./printable-report";
import { ReportResults } from "./report-results";

/**
 * Informe del documento: el diagnóstico de veracidad (maqueta 12). En pantalla se
 * ve la versión interactiva; al imprimir, la versión de impresión (HU-15).
 */
export function ReportView({ report }: { report: Report }) {
  return (
    <>
      <div className="flex flex-col gap-5 print:hidden">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="min-w-0 text-title font-semibold tracking-normal wrap-anywhere text-ink">
            {report.fileName}
          </h2>
          <StatusChip tone="neutral">{report.standard}</StatusChip>
          <span className="flex-1" />
          <PrintButton />
        </div>

        {report.standardNotice ? <p className="text-small">{report.standardNotice}</p> : null}

        <ReportResults report={report} />
      </div>
      <PrintableReport report={report} />
    </>
  );
}
