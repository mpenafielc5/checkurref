"use client";

import { useState } from "react";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { downloadTextFile } from "@/shared/lib/download";
import { fetchBatchExport } from "../api";
import { batchCsvFileName, buildBatchCsv } from "../batch-csv";

const CSV_TYPE = "text/csv;charset=utf-8";

type BatchExportButtonProps = {
  batchId: string;
  /** Un lote sin trabajos no tiene resultados que exportar. */
  disabled: boolean;
};

/** Pide los resultados de cada referencia y descarga el CSV del lote (HU-10). */
export function BatchExportButton({ batchId, disabled }: BatchExportButtonProps) {
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
    <div className="flex flex-col items-start gap-1 md:items-end">
      <button
        type="button"
        onClick={() => void handleExport()}
        disabled={disabled || exporting}
        aria-busy={exporting}
        className={buttonStyles({ variant: "secondary" })}
      >
        {exporting ? "Preparando el archivo…" : "Exportar CSV"}
      </button>
      {error ? (
        <p role="alert" className="text-small text-verdict-contradiction-text">
          {error}
        </p>
      ) : null}
    </div>
  );
}
