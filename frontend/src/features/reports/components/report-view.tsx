import { Printer } from "lucide-react";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { StatusChip } from "@/shared/components/ui/status-chip";
import type { Report } from "../types";
import { ReportResults } from "./report-results";

/** Informe del documento: el diagnóstico de veracidad (maqueta 12). */
export function ReportView({ report }: { report: Report }) {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="min-w-0 text-title font-semibold tracking-normal wrap-anywhere text-ink">
          {report.fileName}
        </h2>
        <StatusChip tone="neutral">{report.standard}</StatusChip>
        <span className="flex-1" />
        {/* Se activa con la vista de impresión del informe (HU-15). */}
        <button type="button" disabled className={buttonStyles({ variant: "secondary" })}>
          <Printer aria-hidden="true" className="size-4" />
          Exportar PDF
        </button>
      </div>

      {report.standardNotice ? <p className="text-small">{report.standardNotice}</p> : null}

      <ReportResults report={report} />
    </div>
  );
}
