import { FileText } from "lucide-react";
import Link from "next/link";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { StatusChip } from "@/shared/components/ui/status-chip";
import { verifiedCount } from "@/shared/lib/analysis-progress";
import { formatFileSize } from "@/shared/lib/format";
import type { BatchUpload, CreatedBatch, UploadState } from "../types";
import { analyzedCount, failedUploads, isAnalyzing, sendProgress } from "../upload-progress";

function UploadStateChip({ state }: { state: UploadState }) {
  switch (state.kind) {
    case "en_espera":
      return <StatusChip tone="neutral">En espera</StatusChip>;
    case "subiendo":
      return <StatusChip tone="info">Subiendo…</StatusChip>;
    case "rechazado":
    case "fallo_subida":
      return <StatusChip tone="danger">No enviado</StatusChip>;
    case "repetido":
      return <StatusChip tone="neutral">Ya está en el lote</StatusChip>;
    case "listo":
      return <StatusChip tone="success">Listo</StatusChip>;
    case "error_analisis":
      return <StatusChip tone="danger">Error</StatusChip>;
    case "en_analisis":
      if (state.status === "en_cola") return <StatusChip tone="neutral">En cola</StatusChip>;
      if (state.status !== "verificando" || !state.totalReferences) {
        return <StatusChip tone="warning">Analizando</StatusChip>;
      }
      return (
        <StatusChip tone="warning">
          Verificando {verifiedCount(state.progress, state.totalReferences)}/{state.totalReferences}
        </StatusChip>
      );
  }
}

/** El motivo del error, si lo hay: un mensaje largo no cabe en la etiqueta. */
function reasonOf(state: UploadState): string | null {
  if (state.kind === "repetido") return "Este PDF ya se había subido; no se analizará de nuevo.";
  return "reason" in state ? state.reason : null;
}

function filesLabel(count: number): string {
  return `${count} ${count === 1 ? "archivo" : "archivos"}`;
}

type BatchUploadProgressProps = {
  batch: CreatedBatch;
  uploads: BatchUpload[];
  sending: boolean;
  slow: boolean;
  onRetry: () => void;
};

/** Estado de cada archivo del lote recién enviado (maqueta 15, HU-08 CA03). */
export function BatchUploadProgress({
  batch,
  uploads,
  sending,
  slow,
  onRetry,
}: BatchUploadProgressProps) {
  const analyzed = analyzedCount(uploads);
  const failed = failedUploads(uploads).length;
  const { current, total } = sendProgress(uploads);

  return (
    <section aria-labelledby="titulo-avance" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 flex-col">
          <h2 id="titulo-avance" className="text-small font-semibold tracking-normal text-ink">
            Avance del lote · {filesLabel(uploads.length)} · {analyzed}{" "}
            {analyzed === 1 ? "analizado" : "analizados"}
          </h2>
          <p className="text-small break-words">
            {batch.name}
            {batch.period ? ` · ${batch.period}` : ""}
          </p>
        </div>
        {/* Salir de la pantalla mientras se envía dejaría archivos sin subir. */}
        {sending ? null : (
          <Link
            href={`/docente/lotes/${batch.id}`}
            className="text-small font-medium text-accent-text hover:underline"
          >
            Ir al tablero del lote →
          </Link>
        )}
      </div>

      <div aria-live="polite" className="flex flex-col gap-1 text-small">
        {sending ? (
          <p>
            Enviando {current} de {total}. Mantén esta página abierta hasta que termine el envío.
          </p>
        ) : null}
        {slow ? (
          <p>Iniciando el motor de análisis; este proceso puede tardar hasta un minuto.</p>
        ) : null}
        {!sending && isAnalyzing(uploads) ? (
          <p>
            El análisis continúa aunque salgas de esta pantalla; podrás consultarlo en el tablero.
          </p>
        ) : null}
      </div>

      <ul className="flex flex-col divide-y divide-hairline rounded-card border border-hairline bg-surface px-4">
        {uploads.map((upload) => {
          const reason = reasonOf(upload.state);
          const isError = upload.state.kind !== "repetido" && reason !== null;
          return (
            <li key={upload.key} className="flex items-center gap-3 py-3">
              <FileText aria-hidden="true" className="size-5 shrink-0 text-body" />
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="text-small font-medium break-all text-ink">
                  {upload.file.name}
                </span>
                <span
                  className={`text-caption ${isError ? "text-verdict-contradiction-text" : "text-body"}`}
                >
                  {reason ?? formatFileSize(upload.file.size)}
                </span>
              </span>
              <UploadStateChip state={upload.state} />
            </li>
          );
        })}
      </ul>

      {failed > 0 && !sending ? (
        <div className="flex">
          <button
            type="button"
            onClick={onRetry}
            className={buttonStyles({ variant: "secondary" })}
          >
            Reintentar{" "}
            {failed === 1 ? "el archivo no enviado" : `los ${failed} archivos no enviados`}
          </button>
        </div>
      ) : null}
    </section>
  );
}
