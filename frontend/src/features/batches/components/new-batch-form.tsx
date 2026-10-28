"use client";

import { FileText } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { PdfDropzone } from "@/shared/components/pdf-dropzone";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { StatusChip } from "@/shared/components/ui/status-chip";
import { formatFileSize } from "@/shared/lib/format";
import type { BatchUpload, UploadState } from "../types";

const INPUT_CLASSES =
  "h-input w-full rounded-control border border-hairline-strong bg-surface px-4 text-small text-ink outline-none focus:border-ink";

function UploadStateChip({ state }: { state: UploadState }) {
  if (state.kind === "listo") return <StatusChip tone="success">Listo</StatusChip>;
  if (state.kind === "verificando") {
    return (
      <StatusChip tone="warning">
        Verificando {state.done}/{state.total}
      </StatusChip>
    );
  }
  return <StatusChip tone="danger">{state.reason}</StatusChip>;
}

function filesLabel(count: number): string {
  return `${count} ${count === 1 ? "archivo" : "archivos"}`;
}

type NewBatchFormProps = {
  batchId: string;
  uploads: BatchUpload[];
};

/**
 * Formulario de nueva auditoría por lote (maqueta 15). El docente elige los PDF
 * (con una ✕ para quitar cualquiera) y los envía juntos; después, cada archivo
 * muestra su avance. El envío y el avance reales llegan con HU-08.
 */
export function NewBatchForm({ batchId, uploads }: NewBatchFormProps) {
  const [chosen, setChosen] = useState(0);
  const analyzed = uploads.filter((upload) => upload.state.kind === "listo").length;

  return (
    <div className="flex flex-col gap-5">
      <form className="flex flex-col gap-4 md:flex-row">
        <label className="flex flex-2 flex-col gap-1.5 text-small">
          Nombre del lote
          <input
            name="nombre"
            defaultValue="Metodología 5B · Ensayo final"
            className={INPUT_CLASSES}
          />
        </label>
        <label className="flex flex-1 flex-col gap-1.5 text-small">
          Periodo
          <input name="periodo" defaultValue="2026-2S" className={INPUT_CLASSES} />
        </label>
      </form>

      <PdfDropzone
        multiple
        title="Arrastra aquí los PDF del curso"
        hint="Hasta 40 archivos de 10 MB cada uno · APA o IEEE (detección automática)"
        pendingMessage="El envío del lote se conecta en la HU-08."
        onChange={(files) => setChosen(files.length)}
      >
        <button type="button" disabled className={`${buttonStyles({ fullWidth: true })} md:w-auto`}>
          Analizar lote ({filesLabel(chosen)})
        </button>
      </PdfDropzone>

      <section aria-labelledby="titulo-avance" className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="titulo-avance" className="text-small font-semibold tracking-normal text-ink">
            Avance del lote · {filesLabel(uploads.length)} · {analyzed} analizados
          </h2>
          <Link
            href={`/docente/lotes/${batchId}`}
            className="text-small font-medium text-accent-text hover:underline"
          >
            Ir al tablero del lote →
          </Link>
        </div>
        <ul className="flex flex-col divide-y divide-hairline rounded-card border border-hairline bg-surface px-4">
          {uploads.map((upload) => (
            <li key={upload.fileName} className="flex flex-wrap items-center gap-x-4 gap-y-2 py-3">
              <FileText aria-hidden="true" className="size-5 text-body" />
              <span className="flex-1 text-small text-ink">{upload.fileName}</span>
              <span className="text-small">{formatFileSize(upload.sizeBytes)}</span>
              <UploadStateChip state={upload.state} />
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
