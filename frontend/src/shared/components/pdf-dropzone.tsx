"use client";

import { CloudUpload } from "lucide-react";
import { useId, useState, type DragEvent } from "react";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { formatFileSize } from "@/shared/lib/format";
import { MAX_FILES_PER_BATCH, validatePdfFile } from "@/shared/lib/pdf-rules";

type PdfDropzoneProps = {
  /** Varios archivos: subida por lote del docente. */
  multiple?: boolean;
  title: string;
  hint: string;
  /** Mensaje mientras la subida real no está conectada. */
  pendingMessage: string;
};

type Selection = { name: string; size: number; error: string | null };

/** Zona para arrastrar o elegir PDF (maquetas 10 y 15). Valida tipo y tamaño. */
export function PdfDropzone({ multiple = false, title, hint, pendingMessage }: PdfDropzoneProps) {
  const inputId = useId();
  const [dragging, setDragging] = useState(false);
  const [selection, setSelection] = useState<Selection[]>([]);

  function handleFiles(list: FileList | null) {
    if (!list) return;
    const files = Array.from(list).slice(0, multiple ? MAX_FILES_PER_BATCH : 1);
    setSelection(
      files.map((file) => {
        const result = validatePdfFile(file);
        return { name: file.name, size: file.size, error: result.ok ? null : result.reason };
      }),
    );
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    handleFiles(event.dataTransfer.files);
  }

  return (
    <div className="flex flex-col gap-3">
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={`flex flex-col items-center gap-3 rounded-panel border-2 border-dashed px-6 py-8 text-center transition-colors ${
          dragging ? "border-primary bg-accent-soft" : "border-hairline-strong bg-canvas-soft"
        }`}
      >
        <CloudUpload aria-hidden="true" className="size-12 text-primary" />
        <p className="text-title font-semibold text-ink">{title}</p>
        <p className="text-small">{hint}</p>
        <label htmlFor={inputId} className={`${buttonStyles()} cursor-pointer`}>
          Seleccionar PDF
        </label>
        <input
          id={inputId}
          type="file"
          accept="application/pdf,.pdf"
          multiple={multiple}
          className="sr-only"
          onChange={(event) => handleFiles(event.target.files)}
        />
      </div>

      {selection.length > 0 ? (
        <div className="flex flex-col gap-2" aria-live="polite">
          <ul className="flex flex-col gap-2">
            {selection.map((file) => (
              <li
                key={file.name}
                className="flex flex-wrap items-center justify-between gap-2 rounded-card border border-hairline px-4 py-2 text-small"
              >
                <span className="font-medium text-ink">{file.name}</span>
                <span className={file.error ? "text-verdict-contradiction-text" : "text-body"}>
                  {file.error ?? formatFileSize(file.size)}
                </span>
              </li>
            ))}
          </ul>
          <p className="text-caption text-body">{pendingMessage}</p>
        </div>
      ) : null}
    </div>
  );
}
