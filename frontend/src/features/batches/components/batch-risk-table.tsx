"use client";

import { ChevronDown, ChevronUp } from "lucide-react";
import Link from "next/link";
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
import { StatusChip, type ChipTone } from "@/shared/components/ui/status-chip";
import { authorsLabel, sortBatchWorks, type SortDirection, type SortKey } from "../rules";
import type { BatchWork, RiskLevel } from "../types";

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

/** Siempre en el mismo orden: quién (autores o el aviso) y debajo el archivo. */
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
      <span className="text-caption break-words text-body">{work.fileName}</span>
    </span>
  );
}

/** Trabajos del lote ordenados por riesgo; cada encabezado ordena (maqueta 16). */
export function BatchRiskTable({ batchId, works }: { batchId: string; works: BatchWork[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("risk");
  const [direction, setDirection] = useState<SortDirection>("desc");

  function toggle(key: SortKey) {
    if (key === sortKey) {
      setDirection(direction === "desc" ? "asc" : "desc");
    } else {
      setSortKey(key);
      setDirection("desc");
    }
  }

  function chooseMobileSort(id: string) {
    const option = MOBILE_SORTS.find((item) => item.id === id);
    if (!option) return;
    setSortKey(option.key);
    setDirection(option.direction);
  }

  const sorted = sortBatchWorks(works, sortKey, direction);
  const mobileSort =
    MOBILE_SORTS.find((item) => item.key === sortKey && item.direction === direction)?.id ?? "";
  const reportHref = (work: BatchWork) => `/docente/lotes/${batchId}/${work.analysisId}`;

  return (
    <>
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
          {sorted.map((work) => (
            <li key={work.analysisId} className="flex">
              <Link href={reportHref(work)} className={`${cardClass} hover:border-hairline-strong`}>
                <span className="flex items-start justify-between gap-3">
                  <WorkIdentity work={work} />
                  <StatusChip tone={RISK_TONES[work.risk]}>
                    Riesgo {RISK_LABELS[work.risk].toLowerCase()}
                  </StatusChip>
                </span>
                <span className="text-small">
                  {work.references} referencias · Índice {work.index} · {work.alerts}{" "}
                  {work.alerts === 1 ? "alerta" : "alertas"}
                </span>
              </Link>
            </li>
          ))}
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
          </tr>
        </thead>
        <tbody>
          {sorted.map((work) => (
            <tr key={work.analysisId} className="hover:bg-canvas-soft">
              <td className={tdClass}>
                <Link href={reportHref(work)} className="group flex">
                  <WorkIdentity work={work} />
                </Link>
              </td>
              <td className={`${tdClass} ${numericClass}`}>{work.references}</td>
              <td className={`${tdClass} ${numericClass}`}>{work.index}</td>
              <td className={`${tdClass} ${numericClass}`}>{work.alerts}</td>
              <td className={`${tdClass} font-semibold ${RISK_CLASSES[work.risk]}`}>
                {RISK_LABELS[work.risk]}
              </td>
            </tr>
          ))}
        </tbody>
      </DataTable>
    </>
  );
}
