import Link from "next/link";
import { SkeletonText } from "@/shared/components/ui/skeleton";
import { StatusChip } from "@/shared/components/ui/status-chip";
import type { BatchStatus, BatchSummary } from "../types";

function BatchStatusChip({ status, works }: { status: BatchStatus; works: number }) {
  if (status.kind === "analyzing") {
    return (
      <StatusChip tone="warning">
        Analizando {status.done}/{works}
      </StatusChip>
    );
  }
  // Verde solo sin alertas: cualquier alerta pide revisión.
  if (status.count === 0) return <StatusChip tone="success">Sin alertas</StatusChip>;
  const tone = status.count >= 5 ? "danger" : "warning";
  return (
    <StatusChip tone={tone}>
      {status.count} {status.count === 1 ? "alerta" : "alertas"}
    </StatusChip>
  );
}

const ROW_CLASSES =
  "flex w-full flex-wrap items-center gap-x-5 gap-y-2 rounded-card border border-hairline bg-canvas px-5 py-3";

/** Lista de lotes del docente (maqueta 14). Cada lote abre su tablero. */
export function BatchList({ batches }: { batches: BatchSummary[] }) {
  return (
    <ul className="flex flex-col gap-2">
      {batches.map((batch) => (
        <li key={batch.id} className="flex">
          <Link
            href={`/docente/lotes/${batch.id}`}
            className={`${ROW_CLASSES} hover:border-hairline-strong`}
          >
            <span className="flex flex-1 flex-col">
              <span className="font-semibold text-ink">{batch.name}</span>
              <span className="text-small">
                {batch.works} trabajos · <span className="whitespace-nowrap">{batch.period}</span>
              </span>
            </span>
            <BatchStatusChip status={batch.status} works={batch.works} />
          </Link>
        </li>
      ))}
    </ul>
  );
}

/** Esqueleto de BatchList: nombre, detalle y la etiqueta de estado. */
export function BatchListSkeleton({ rows }: { rows: number }) {
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className={ROW_CLASSES}>
          <span className="flex flex-1 flex-col">
            <SkeletonText widthClass="w-48 max-w-full" />
            <SkeletonText textClass="text-small" widthClass="w-36 max-w-full" />
          </span>
          <span className="flex px-3 py-0.5">
            <SkeletonText textClass="text-caption" widthClass="w-16" />
          </span>
        </div>
      ))}
    </div>
  );
}
