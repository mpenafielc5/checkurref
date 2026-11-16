import { StatusChip } from "@/shared/components/ui/status-chip";
import type { Report } from "../types";
import { OriginalPdfButton } from "./original-pdf";
import { PrintButton } from "./print-button";
import { PrintableReport } from "./printable-report";
import { ReportResults } from "./report-results";

/**
 * Informe del documento: el diagnóstico de veracidad (maqueta 12). En pantalla se
 * ve la versión interactiva; al imprimir, la versión de impresión (HU-15). El PDF
 * original se puede abrir para revisar lo que el informe no muestra (la portada);
 * su enlace lo pide ReportLoader, junto con el informe.
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
          {/* En el celular, los dos botones comparten una fila; en pantallas anchas, a la derecha. */}
          <div className="flex w-full gap-3 *:flex-1 md:w-auto md:*:flex-none">
            <OriginalPdfButton />
            <PrintButton />
          </div>
        </div>

        {report.standardNotice ? <p className="text-small">{report.standardNotice}</p> : null}

        <ReportResults report={report} />
      </div>
      <PrintableReport report={report} />
    </>
  );
}
