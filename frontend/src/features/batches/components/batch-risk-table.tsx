"use client";

import { ChevronDown, ChevronUp } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import {
  DataTable,
  numericClass,
  tableHeadClass,
  tdClass,
  thClass,
} from "@/shared/components/ui/data-table";
import { sortBatchWorks, type SortDirection, type SortKey } from "../rules";
import type { BatchWork, RiskLevel } from "../types";

const RISK_CLASSES: Record<RiskLevel, string> = {
  alto: "text-verdict-contradiction-text",
  medio: "text-verdict-discrepancy-text",
  bajo: "text-verdict-verified-text",
};

const RISK_LABELS: Record<RiskLevel, string> = { alto: "Alto", medio: "Medio", bajo: "Bajo" };

const COLUMNS: { key: SortKey; label: string; numeric: boolean }[] = [
  { key: "name", label: "Trabajo", numeric: false },
  { key: "references", label: "Refs", numeric: true },
  { key: "index", label: "Índice", numeric: true },
  { key: "alerts", label: "Alertas", numeric: true },
  { key: "risk", label: "Riesgo", numeric: false },
];

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

  const sorted = sortBatchWorks(works, sortKey, direction);

  return (
    <DataTable caption="Trabajos del lote ordenados por riesgo">
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
          <tr key={work.name} className="hover:bg-canvas-soft">
            <td className={tdClass}>
              <Link
                href={`/docente/lotes/${batchId}/${work.analysisId}`}
                className="font-medium hover:text-accent-text"
              >
                {work.name}
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
  );
}
