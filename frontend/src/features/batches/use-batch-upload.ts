import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import type { RejectedPdf } from "@/shared/components/pdf-dropzone";
import { createBatch, fetchBatchProgress, submitBatchWork, wakeApi } from "./api";
import type { BatchUpload, CreatedBatch, UploadState } from "./types";
import {
  allSentCleanly,
  applyWorksProgress,
  failedUploads,
  initialUploads,
  isAnalyzing,
  stateAfterUpload,
} from "./upload-progress";

/** Cada cuánto se consulta el avance del lote mientras hay análisis en curso. */
export const POLL_MS = 10_000;

/**
 * Crea el lote y envía sus archivos uno por uno (HU-08): el error de uno no
 * detiene a los demás (RNF09). Después consulta el avance hasta que terminen.
 * Si un archivo falla, reintentar lo envía al mismo lote, sin crear otro.
 */
export function useBatchUpload() {
  const [batch, setBatch] = useState<CreatedBatch | null>(null);
  const [uploads, setUploads] = useState<BatchUpload[]>([]);
  const [creating, setCreating] = useState(false);
  const [sending, setSending] = useState(false);
  const [slow, setSlow] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const router = useRouter();
  const batchId = batch?.id ?? null;
  const polling = isAnalyzing(uploads);
  const sentCleanly = !sending && allSentCleanly(uploads);

  useEffect(() => {
    wakeApi();
  }, []);

  // Si todo se envió sin problemas, el avance se sigue en el tablero: no hace falta
  // un clic más. Con rechazados, fallidos o repetidos se queda aquí para leer el motivo.
  useEffect(() => {
    if (batchId && sentCleanly) router.push(`/docente/lotes/${encodeURIComponent(batchId)}`);
  }, [batchId, sentCleanly, router]);

  // Cerrar la pestaña corta el envío de los archivos que faltan: se pide confirmar.
  const busy = creating || sending;
  useEffect(() => {
    if (!busy) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [busy]);

  // Cada consulta espera a la anterior: una respuesta atrasada no hace retroceder el avance.
  useEffect(() => {
    if (!batchId || !polling) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      const works = await fetchBatchProgress(batchId);
      if (!active) return;
      if (works) setUploads((current) => applyWorksProgress(current, works));
      timer = setTimeout(poll, POLL_MS);
    };
    timer = setTimeout(poll, POLL_MS);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [batchId, polling]);

  function setState(key: string, state: UploadState) {
    setUploads((current) =>
      current.map((upload) => (upload.key === key ? { ...upload, state } : upload)),
    );
  }

  async function send(id: string, pending: BatchUpload[]) {
    setSending(true);
    for (const upload of pending) {
      setState(upload.key, { kind: "subiendo" });
      const outcome = await submitBatchWork(id, upload.file, () => setSlow(true));
      setSlow(false);
      setState(upload.key, stateAfterUpload(outcome));
    }
    setSending(false);
  }

  async function start(name: string, period: string, files: File[], rejected: RejectedPdf[]) {
    setCreating(true);
    setCreateError(null);
    const outcome = await createBatch(name, period, () => setSlow(true));
    setSlow(false);
    setCreating(false);
    if (outcome.kind === "error") {
      setCreateError(outcome.message);
      return;
    }
    const initial = initialUploads(files, rejected);
    setBatch(outcome.batch);
    setUploads(initial);
    await send(
      outcome.batch.id,
      initial.filter((upload) => upload.state.kind === "en_espera"),
    );
  }

  /** Agrega archivos a un lote que ya existe: no se crea otro. */
  async function addTo(existing: CreatedBatch, files: File[], rejected: RejectedPdf[]) {
    setCreateError(null);
    const initial = initialUploads(files, rejected);
    setBatch(existing);
    setUploads(initial);
    await send(
      existing.id,
      initial.filter((upload) => upload.state.kind === "en_espera"),
    );
  }

  async function retry() {
    if (!batchId || sending) return;
    await send(batchId, failedUploads(uploads));
  }

  /** Olvida el lote mostrado para empezar otro; el anterior sigue en su tablero. */
  const reset = useCallback(() => {
    setBatch(null);
    setUploads([]);
    setSlow(false);
    setCreateError(null);
  }, []);

  return { batch, uploads, creating, sending, slow, createError, start, addTo, retry, reset };
}
