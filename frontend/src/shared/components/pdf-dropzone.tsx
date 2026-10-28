"use client";

import { CloudUpload, FileCheck2, FileText, FileX2, X } from "lucide-react";
import { useId, useRef, useState, type DragEvent, type ReactNode } from "react";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { formatFileSize } from "@/shared/lib/format";
import { MAX_FILES_PER_BATCH, validatePdfFile } from "@/shared/lib/pdf-rules";

type PdfDropzoneProps = {
  /** Varios archivos: subida por lote del docente. */
  multiple?: boolean;
  title: string;
  hint: string;
  /** Mensaje mientras la subida real no está conectada. */
  pendingMessage?: string;
  /** Recibe los archivos válidos cada vez que cambia la selección. */
  onChange?: (files: File[]) => void;
  /** Mientras se sube, no se puede cambiar la selección. */
  disabled?: boolean;
  /** Acción principal (Analizar…), dentro del mismo contenedor que los archivos. */
  children?: ReactNode;
};

type Item = { key: string; file: File; error: string | null };

/** Un solo contenedor: punteado mientras espera, continuo cuando ya tiene archivos. */
const BOX_CLASSES = "flex flex-col rounded-panel border-2 px-6 py-8 transition-colors";
/** El estado vacío y el de un archivo miden lo mismo: al elegir, nada se mueve. */
const FIXED_HEIGHT = "min-h-dropzone items-center justify-center md:min-h-dropzone-wide";
const REMOVE_CLASSES =
  "inline-flex size-control shrink-0 items-center justify-center rounded-pill text-body hover:bg-hairline-soft hover:text-ink disabled:opacity-70";

function keyOf(file: File): string {
  return `${file.name}·${file.size}·${file.lastModified}`;
}

/**
 * Zona para arrastrar o elegir PDF (maquetas 10 y 15). Valida tipo y tamaño.
 * - Un archivo (estudiante): al elegirlo, el recuadro pasa a línea continua y
 *   muestra el archivo en una fila, con una ✕ para quitarlo y la acción
 *   principal. Para reemplazarlo: quitarlo o soltar otro encima.
 * - Varios (docente): una lista limpia con una ✕ por archivo; los inválidos
 *   se muestran en rojo con su motivo y no se envían. "Agregar más" suma
 *   archivos sin perder los anteriores, hasta 40.
 */
export function PdfDropzone({
  multiple = false,
  title,
  hint,
  pendingMessage,
  onChange,
  disabled = false,
  children,
}: PdfDropzoneProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [items, setItems] = useState<Item[]>([]);
  const [overLimit, setOverLimit] = useState(false);

  function update(next: Item[]) {
    setItems(next);
    onChange?.(next.filter((item) => !item.error).map((item) => item.file));
    // Sin esto, volver a elegir el mismo archivo no dispararía el cambio.
    if (inputRef.current) inputRef.current.value = "";
  }

  function handleFiles(list: FileList | null) {
    if (!list || list.length === 0) return;
    const incoming = Array.from(list).map((file) => {
      const result = validatePdfFile(file);
      return { key: keyOf(file), file, error: result.ok ? null : result.reason };
    });
    if (!multiple) {
      setOverLimit(false);
      update(incoming.slice(0, 1));
      return;
    }
    const known = new Set(items.map((item) => item.key));
    const merged = [...items, ...incoming.filter((item) => !known.has(item.key))];
    setOverLimit(merged.length > MAX_FILES_PER_BATCH);
    update(merged.slice(0, MAX_FILES_PER_BATCH));
  }

  function remove(key: string) {
    setOverLimit(false);
    update(items.filter((item) => item.key !== key));
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    if (!disabled) handleFiles(event.dataTransfer.files);
  }

  const single = !multiple && items.length === 1 && !items[0].error ? items[0] : null;
  const showList = multiple && items.length > 0;
  const filled = Boolean(single) || showList;
  const pickerDisabled = disabled ? "cursor-not-allowed opacity-70" : "cursor-pointer";

  return (
    <div className="flex flex-col gap-3">
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={`${BOX_CLASSES} ${showList ? "gap-4" : `${FIXED_HEIGHT} gap-3 text-center`} ${
          dragging
            ? "border-dashed border-primary bg-accent-soft"
            : filled
              ? "border-solid border-hairline-strong bg-surface"
              : "border-dashed border-hairline-strong bg-canvas-soft"
        }`}
      >
        {single ? (
          <div className="flex w-full max-w-3xl flex-col gap-4 md:flex-row md:items-center">
            {/* Una fila sin borde propio: el recuadro ya es el contenedor. */}
            <div className="flex min-w-0 flex-1 items-center gap-4 text-left">
              <FileCheck2 aria-hidden="true" className="size-8 shrink-0 text-verdict-verified" />
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="font-semibold break-all text-ink">{single.file.name}</span>
                <span className="text-small">
                  {formatFileSize(single.file.size)} · Listo para analizar
                </span>
              </span>
              <button
                type="button"
                onClick={() => remove(single.key)}
                disabled={disabled}
                aria-label={`Quitar ${single.file.name}`}
                title="Quitar archivo"
                className={REMOVE_CLASSES}
              >
                <X aria-hidden="true" className="size-5" />
              </button>
            </div>
            {children}
          </div>
        ) : showList ? (
          <>
            <ul aria-label="Archivos elegidos" className="flex flex-col divide-y divide-hairline">
              {items.map((item) => (
                <li key={item.key} className="flex items-center gap-3 py-2 first:pt-0">
                  {item.error ? (
                    <FileX2
                      aria-hidden="true"
                      className="size-5 shrink-0 text-verdict-contradiction-text"
                    />
                  ) : (
                    <FileText aria-hidden="true" className="size-5 shrink-0 text-body" />
                  )}
                  <span className="flex min-w-0 flex-1 flex-col md:flex-row md:items-center md:gap-3">
                    <span className="min-w-0 text-small font-medium break-all text-ink md:flex-1">
                      {item.file.name}
                    </span>
                    <span
                      className={`text-caption ${
                        item.error ? "text-verdict-contradiction-text" : "text-body"
                      }`}
                    >
                      {item.error ?? formatFileSize(item.file.size)}
                    </span>
                  </span>
                  <button
                    type="button"
                    onClick={() => remove(item.key)}
                    disabled={disabled}
                    aria-label={`Quitar ${item.file.name}`}
                    title="Quitar archivo"
                    className={REMOVE_CLASSES}
                  >
                    <X aria-hidden="true" className="size-5" />
                  </button>
                </li>
              ))}
            </ul>
            {overLimit ? (
              <p className="text-small text-verdict-discrepancy-text">
                Un lote admite hasta {MAX_FILES_PER_BATCH} archivos; se conservaron los{" "}
                {MAX_FILES_PER_BATCH} primeros.
              </p>
            ) : null}
            <div className="flex flex-col-reverse gap-2 md:flex-row md:justify-end">
              <label
                htmlFor={inputId}
                aria-disabled={disabled}
                className={`${buttonStyles({ variant: "secondary", fullWidth: true })} md:w-auto ${pickerDisabled}`}
              >
                Agregar más
              </label>
              {children}
            </div>
          </>
        ) : (
          <>
            <CloudUpload aria-hidden="true" className="size-12 text-primary" />
            <p className="text-title font-semibold text-ink">{title}</p>
            <p className="text-small">{hint}</p>
            <label
              htmlFor={inputId}
              aria-disabled={disabled}
              className={`${buttonStyles()} ${pickerDisabled}`}
            >
              Seleccionar PDF
            </label>
          </>
        )}
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept="application/pdf,.pdf"
          multiple={multiple}
          disabled={disabled}
          className="sr-only"
          onChange={(event) => handleFiles(event.target.files)}
        />
      </div>

      {/* Un archivo inválido en la subida individual: el recuadro sigue vacío y se explica por qué. */}
      {!multiple && items.length === 1 && items[0].error ? (
        <p role="alert" className="text-small text-verdict-contradiction-text">
          {items[0].file.name}: {items[0].error}
        </p>
      ) : null}
      {showList && pendingMessage ? (
        <p className="text-caption text-body">{pendingMessage}</p>
      ) : null}
    </div>
  );
}
