import Link from "next/link";
import { SkeletonText } from "@/shared/components/ui/skeleton";
import { StatusChip } from "@/shared/components/ui/status-chip";
import type { BatchStatus, BatchSummary } from "../types";

function BatchStatusChip({ status, works }: { status: BatchStatus; works: number }) {
  if (status.kind === "empty") return <StatusChip tone="neutral">Sin trabajos</StatusChip>;
  if (status.kind === "failed") return <StatusChip tone="danger">Sin analizar</StatusChip>;
  if (status.kind === "analyzing") {
    return (
      <StatusChip tone="warning">
        Analizando {status.done}/{works}
      </StatusChip>
    );
  }
  if (status.highRisk === 0) return <StatusChip tone="success">Sin riesgo alto</StatusChip>;
  return <StatusChip tone="danger">{status.highRisk} de riesgo alto</StatusChip>;
}

function detailLine(batch: BatchSummary): string[] {
  const parts = [`${batch.works} ${batch.works === 1 ? "trabajo" : "trabajos"}`];
  if (batch.period) parts.push(batch.period);
  if (batch.failed > 0) parts.push(`${batch.failed} con error`);
  return parts;
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
              <span className="font-semibold wrap-anywhere text-ink">{batch.name}</span>
              <span className="text-small">{detailLine(batch).join(" · ")}</span>
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
