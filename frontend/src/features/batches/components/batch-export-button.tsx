"use client";

import { Download } from "lucide-react";
import { useState } from "react";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { downloadTextFile } from "@/shared/lib/download";
import { fetchBatchExport } from "../api";
import { batchCsvFileName, buildBatchCsv } from "../batch-csv";
import { Notice } from "@/shared/components/ui/notice";

const CSV_TYPE = "text/csv;charset=utf-8";

type BatchExportButtonProps = {
  batchId: string;
  /** Un lote sin trabajos no tiene resultados que exportar. */
  disabled: boolean;
  /** Ancho dentro de la fila de acciones. */
  className?: string;
};

/** Pide los resultados de cada referencia y descarga el CSV del lote (HU-10). */
export function BatchExportButton({ batchId, disabled, className = "" }: BatchExportButtonProps) {
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleExport() {
    setExporting(true);
    setError(null);
    const outcome = await fetchBatchExport(batchId);
    setExporting(false);
    if (outcome.kind === "error") {
      setError(outcome.message);
      return;
    }
    downloadTextFile(batchCsvFileName(outcome.batch.name), buildBatchCsv(outcome.batch), CSV_TYPE);
  }

  return (
    <div className={`flex flex-col items-stretch gap-1 md:items-end ${className}`}>
      <button
        type="button"
        onClick={() => void handleExport()}
        disabled={disabled || exporting}
        aria-busy={exporting}
        className={`${buttonStyles({ variant: "secondary", fullWidth: true })} md:w-auto`}
      >
        <Download aria-hidden="true" className="size-4" />
        {exporting ? "Preparando el archivo…" : "Exportar CSV"}
      </button>
      {error ? <Notice tone="error">{error}</Notice> : null}
    </div>
  );
}
