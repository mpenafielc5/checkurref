"use client";

import { ChevronDown, ChevronUp } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import {
  cardClass,
  cardListClass,
  DataTable,
  numericClass,
  tableHeadClass,
  tdClass,
  thClass,
} from "@/shared/components/ui/data-table";
import { Pagination } from "@/shared/components/ui/pagination";
import { StatusChip, type ChipTone } from "@/shared/components/ui/status-chip";
import { DeleteWorkButton } from "@/shared/components/delete-work-button";
import { formatIndex } from "@/shared/lib/format";
import { PAGE_PARAM, paginate, parsePage } from "@/shared/lib/pagination";
import {
  authorsLabel,
  isWorkCompleted,
  sortBatchWorks,
  type SortDirection,
  type SortKey,
} from "../rules";
import type { BatchWork, RiskLevel } from "../types";
import { ANALYSIS_FAILED } from "../upload-progress";
import { AnalysisStatusChip } from "./analysis-status-chip";

/** RF20-CA03: la tabla se pagina de 20 en 20. */
const WORKS_PAGE_SIZE = 20;
const TABLE_ID = "trabajos-del-lote";
/** Lo que aún no existe en la fila: el trabajo no terminó o no hay con qué calcularlo. */
const NO_VALUE = "—";

const RISK_CLASSES: Record<RiskLevel, string> = {
  alto: "text-verdict-contradiction-text",
  medio: "text-verdict-discrepancy-text",
  bajo: "text-verdict-verified-text",
};

const RISK_TONES: Record<RiskLevel, ChipTone> = {
  alto: "danger",
  medio: "warning",
  bajo: "success",
};

const RISK_LABELS: Record<RiskLevel, string> = { alto: "Alto", medio: "Medio", bajo: "Bajo" };

const COLUMNS: { key: SortKey; label: string; numeric: boolean }[] = [
  { key: "name", label: "Trabajo", numeric: false },
  { key: "references", label: "Refs", numeric: true },
  { key: "index", label: "Índice", numeric: true },
  { key: "alerts", label: "Alertas", numeric: true },
  { key: "risk", label: "Riesgo", numeric: false },
];

/** Órdenes del selector del celular, donde no hay encabezados que tocar. */
const MOBILE_SORTS: { id: string; label: string; key: SortKey; direction: SortDirection }[] = [
  { id: "riesgo", label: "Mayor riesgo", key: "risk", direction: "desc" },
  { id: "indice", label: "Menor índice", key: "index", direction: "asc" },
  { id: "alertas", label: "Más alertas", key: "alerts", direction: "desc" },
  { id: "referencias", label: "Más referencias", key: "references", direction: "desc" },
  { id: "nombre", label: "Nombre (A–Z)", key: "name", direction: "asc" },
];

/** Siempre en el mismo orden: quién (autores o el aviso), el archivo y, si falló, el motivo. */
function WorkIdentity({ work }: { work: BatchWork }) {
  const authors = authorsLabel(work);
  return (
    <span className="flex min-w-0 flex-col">
      {authors ? (
        <span className="font-semibold break-words text-ink group-hover:text-accent-text">
          {authors}
        </span>
      ) : (
        <span className="font-semibold text-muted italic group-hover:text-accent-text">
          Portada no reconocida
        </span>
      )}
      <span className="text-caption wrap-anywhere text-body">{work.fileName}</span>
      {work.status === "error" ? (
        <span className="text-caption text-verdict-contradiction-text">
          {work.errorMessage ?? ANALYSIS_FAILED}
        </span>
      ) : null}
    </span>
  );
}

/** Estado de un trabajo que no tiene un riesgo que mostrar. */
function PendingState({ work }: { work: BatchWork }) {
  if (work.status === "error") return <StatusChip tone="danger">Error</StatusChip>;
  if (isWorkCompleted(work)) return <StatusChip tone="neutral">Sin calcular</StatusChip>;
  return (
    <AnalysisStatusChip
      status={work.status}
      progress={work.progress}
      totalReferences={work.references}
    />
  );
}

function metricOf(work: BatchWork, value: number | null): string {
  return isWorkCompleted(work) && value !== null ? String(value) : NO_VALUE;
}

function mobileSummary(work: BatchWork): string {
  const references = `${work.references ?? 0} referencias`;
  const alerts = `${work.alerts} ${work.alerts === 1 ? "alerta" : "alertas"}`;
  return `${references} · Índice ${work.index === null ? NO_VALUE : formatIndex(work.index)} · ${alerts}`;
}

/** Trabajos del lote ordenados por riesgo; cada encabezado ordena (maqueta 16). */
type BatchRiskTableProps = {
  batchId: string;
  works: BatchWork[];
  /** Tras eliminar un trabajo, el tablero se vuelve a pedir. */
  onDeleted?: () => void;
};

/** Un análisis en curso todavía escribe sus resultados: se elimina cuando termina. */
function isFinished(work: BatchWork): boolean {
  return isWorkCompleted(work) || work.status === "error";
}

export function BatchRiskTable({ batchId, works, onDeleted }: BatchRiskTableProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [sortKey, setSortKey] = useState<SortKey>("risk");
  const [direction, setDirection] = useState<SortDirection>("desc");

  const slice = paginate(
    sortBatchWorks(works, sortKey, direction),
    parsePage(searchParams.get(PAGE_PARAM)),
    WORKS_PAGE_SIZE,
  );

  /** Un orden nuevo empieza desde sus primeros trabajos, no desde la página en que se estaba. */
  function applySort(key: SortKey, nextDirection: SortDirection) {
    setSortKey(key);
    setDirection(nextDirection);
    if (slice.page === 1) return;
    const params = new URLSearchParams(searchParams.toString());
    params.delete(PAGE_PARAM);
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }

  function toggle(key: SortKey) {
    if (key === sortKey) {
      applySort(key, direction === "desc" ? "asc" : "desc");
    } else {
      applySort(key, key === "name" ? "asc" : "desc");
    }
  }

  function chooseMobileSort(id: string) {
    const option = MOBILE_SORTS.find((item) => item.id === id);
    if (option) applySort(option.key, option.direction);
  }

  const mobileSort =
    MOBILE_SORTS.find((item) => item.key === sortKey && item.direction === direction)?.id ?? "";
  const reportHref = (work: BatchWork) => `/docente/lotes/${batchId}/${work.analysisId}`;

  return (
    <div id={TABLE_ID} className="flex scroll-mt-6 flex-col gap-3">
      <div className="flex flex-col gap-3 md:hidden">
        <label className="flex items-center gap-2 text-small">
          Ordenar por
          <select
            value={mobileSort}
            onChange={(event) => chooseMobileSort(event.target.value)}
            className="h-control flex-1 rounded-control border border-hairline-strong bg-surface px-3 text-small text-ink"
          >
            {mobileSort === "" ? <option value="">Orden personalizado</option> : null}
            {MOBILE_SORTS.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <ul className={cardListClass}>
          {slice.items.map((work) => {
            const completed = isWorkCompleted(work);
            const content = (
              <>
                <span className="flex items-start justify-between gap-3">
                  <WorkIdentity work={work} />
                  {work.risk ? (
                    <StatusChip tone={RISK_TONES[work.risk]}>
                      Riesgo {RISK_LABELS[work.risk].toLowerCase()}
                    </StatusChip>
                  ) : (
                    <PendingState work={work} />
                  )}
                </span>
                {completed ? <span className="text-small">{mobileSummary(work)}</span> : null}
              </>
            );
            const body = "flex min-w-0 flex-1 flex-col gap-2";
            return (
              <li
                key={work.analysisId}
                className={`${cardClass} flex-row items-start has-[a:hover]:border-hairline-strong`}
              >
                {completed ? (
                  <Link href={reportHref(work)} className={body}>
                    {content}
                  </Link>
                ) : (
                  <div className={body}>{content}</div>
                )}
                {onDeleted && isFinished(work) ? (
                  <DeleteWorkButton
                    analysisId={work.analysisId}
                    fileName={work.fileName}
                    onDeleted={onDeleted}
                  />
                ) : null}
              </li>
            );
          })}
        </ul>
      </div>

      <DataTable caption="Trabajos del lote ordenados por riesgo" cardsOnMobile>
        <thead className={tableHeadClass}>
          <tr>
            {COLUMNS.map((column) => {
              const active = column.key === sortKey;
              return (
                <th
                  key={column.key}
                  scope="col"
                  aria-sort={active ? (direction === "desc" ? "descending" : "ascending") : "none"}
                  className={`${thClass} ${column.numeric ? numericClass : ""}`}
                >
                  <button
                    type="button"
                    onClick={() => toggle(column.key)}
                    className={`inline-flex items-center gap-1 hover:text-ink ${active ? "text-ink" : ""}`}
                  >
                    {column.label}
                    {active ? (
                      direction === "desc" ? (
                        <ChevronDown aria-hidden="true" className="size-4" />
                      ) : (
                        <ChevronUp aria-hidden="true" className="size-4" />
                      )
                    ) : null}
                  </button>
                </th>
              );
            })}
            {onDeleted ? (
              <th scope="col" className={thClass}>
                <span className="sr-only">Acciones</span>
              </th>
            ) : null}
          </tr>
        </thead>
        <tbody>
          {slice.items.map((work) => (
            <tr key={work.analysisId} className="hover:bg-canvas-soft">
              <td className={tdClass}>
                {isWorkCompleted(work) ? (
                  <Link href={reportHref(work)} className="group flex">
                    <WorkIdentity work={work} />
                  </Link>
                ) : (
                  <WorkIdentity work={work} />
                )}
              </td>
              <td className={`${tdClass} ${numericClass}`}>{metricOf(work, work.references)}</td>
              <td className={`${tdClass} ${numericClass}`}>
                {isWorkCompleted(work) && work.index !== null ? formatIndex(work.index) : NO_VALUE}
              </td>
              <td className={`${tdClass} ${numericClass}`}>{metricOf(work, work.alerts)}</td>
              <td
                className={`${tdClass} ${work.risk ? `font-semibold ${RISK_CLASSES[work.risk]}` : ""}`}
              >
                {work.risk ? RISK_LABELS[work.risk] : <PendingState work={work} />}
              </td>
              {onDeleted ? (
                <td className={`${tdClass} py-1 text-right`}>
                  {isFinished(work) ? (
                    <DeleteWorkButton
                      analysisId={work.analysisId}
                      fileName={work.fileName}
                      onDeleted={onDeleted}
                    />
                  ) : null}
                </td>
              ) : null}
            </tr>
          ))}
        </tbody>
      </DataTable>

      <Pagination
        slice={slice}
        pathname={pathname}
        query={searchParams.toString()}
        noun="trabajos"
        anchorId={TABLE_ID}
      />
    </div>
  );
}
