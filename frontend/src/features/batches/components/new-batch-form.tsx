"use client";

import { useEffect, useLayoutEffect, useRef, useState, type FormEvent } from "react";
import { PdfDropzone, type RejectedPdf } from "@/shared/components/pdf-dropzone";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { useBatchUpload } from "../use-batch-upload";
import { BatchUploadProgress } from "./batch-upload-progress";

const INPUT_CLASSES =
  "h-input w-full rounded-control border border-hairline-strong bg-surface px-4 text-small text-ink outline-none placeholder:text-muted focus:border-ink";

/** Los mismos límites que t_lotes_auditoria. */
const MAX_NAME_LENGTH = 150;
const MAX_PERIOD_LENGTH = 20;

function filesLabel(count: number): string {
  return `${count} ${count === 1 ? "archivo" : "archivos"}`;
}

/**
 * Nueva auditoría por lote (maqueta 15, HU-08). El docente nombra el lote, elige
 * los PDF (con una ✕ para quitar cualquiera) y los envía juntos; después, cada
 * archivo muestra su estado. Si el lote no se puede crear, la selección se conserva.
 */
export function NewBatchForm() {
  const { batch, uploads, creating, sending, slow, createError, start, retry, reset } =
    useBatchUpload();
  const [name, setName] = useState("");
  const [period, setPeriod] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [rejected, setRejected] = useState<RejectedPdf[]>([]);
  const [missingData, setMissingData] = useState(false);
  /** Cambiarla vuelve a montar la zona de subida, que guarda los archivos elegidos. */
  const [dropzoneKey, setDropzoneKey] = useState(0);

  const busyRef = useRef(false);
  useEffect(() => {
    busyRef.current = creating || sending;
  }, [creating, sending]);

  // Next.js oculta la página al navegar y conserva su estado. Al volver, Nueva auditoría
  // empieza de cero; solo se conserva el avance si todavía se están enviando archivos.
  useLayoutEffect(() => {
    return () => {
      if (busyRef.current) return;
      reset();
      setName("");
      setPeriod("");
      setFiles([]);
      setRejected([]);
      setMissingData(false);
      setDropzoneKey((key) => key + 1);
    };
  }, [reset]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanName = name.trim();
    const cleanPeriod = period.trim();
    // Solo con espacios, el navegador da el campo por lleno.
    setMissingData(!cleanName || !cleanPeriod);
    if (cleanName && cleanPeriod && files.length > 0 && !creating) {
      void start(cleanName, cleanPeriod, files, rejected);
    }
  }

  if (batch) {
    return (
      <BatchUploadProgress
        batch={batch}
        uploads={uploads}
        sending={sending}
        slow={slow}
        onRetry={() => void retry()}
      />
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <div className="flex flex-col gap-4 md:flex-row">
        <label className="flex flex-2 flex-col gap-1.5 text-small">
          Nombre del lote
          <input
            name="nombre"
            autoComplete="off"
            required
            maxLength={MAX_NAME_LENGTH}
            value={name}
            onChange={(event) => setName(event.target.value)}
            disabled={creating}
            placeholder="Ej.: Metodología 5B · Ensayo final"
            className={INPUT_CLASSES}
          />
        </label>
        <label className="flex flex-1 flex-col gap-1.5 text-small">
          Periodo
          <input
            name="periodo"
            autoComplete="off"
            required
            maxLength={MAX_PERIOD_LENGTH}
            value={period}
            onChange={(event) => setPeriod(event.target.value)}
            disabled={creating}
            placeholder="Ej.: 2026-2S"
            className={INPUT_CLASSES}
          />
        </label>
      </div>

      <PdfDropzone
        key={dropzoneKey}
        multiple
        title="Arrastra aquí los PDF del curso"
        hint="Hasta 40 archivos de 10 MB cada uno · APA o IEEE (detección automática)"
        disabled={creating}
        onChange={setFiles}
        onRejected={setRejected}
      >
        <button
          type="submit"
          disabled={files.length === 0 || creating}
          aria-busy={creating}
          className={`${buttonStyles({ fullWidth: true })} md:w-auto`}
        >
          {creating ? "Creando el lote…" : `Analizar lote (${filesLabel(files.length)})`}
        </button>
      </PdfDropzone>

      <div aria-live="polite" className="flex flex-col gap-1 text-small">
        {slow ? (
          <p>Iniciando el motor de análisis; este proceso puede tardar hasta un minuto.</p>
        ) : null}
        {missingData ? (
          <p role="alert" className="text-verdict-contradiction-text">
            Escribe el nombre y el periodo del lote.
          </p>
        ) : null}
        {createError ? (
          <p role="alert" className="text-verdict-contradiction-text">
            {createError}
          </p>
        ) : null}
      </div>
    </form>
  );
}
