"use client";

import { Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import {
  DataTable,
  DataTableSkeleton,
  numericClass,
  tableHeadClass,
  tdClass,
  thClass,
} from "@/shared/components/ui/data-table";
import { SkeletonText } from "@/shared/components/ui/skeleton";
import { workHref } from "../sample-data";
import type { WorkVersion } from "../types";

const SEARCH_CLASSES =
  "flex h-input w-full items-center gap-2 rounded-control border border-hairline-strong bg-canvas px-4 md:max-w-xs";

/** Historial de trabajos con búsqueda por nombre (maqueta 13). */
export function WorkHistory({ works }: { works: WorkVersion[] }) {
  const [query, setQuery] = useState("");
  const visible = works.filter((work) =>
    work.fileName.toLowerCase().includes(query.trim().toLowerCase()),
  );

  return (
    <div className="flex flex-col gap-4">
      <label className={SEARCH_CLASSES}>
        <Search aria-hidden="true" className="size-5 text-muted" />
        <span className="sr-only">Buscar trabajo</span>
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Buscar trabajo…"
          className="w-full bg-transparent text-small text-ink outline-none placeholder:text-muted"
        />
      </label>

      <DataTable caption="Historial de trabajos y versiones">
        <thead className={tableHeadClass}>
          <tr>
            <th scope="col" className={thClass}>
              Trabajo
            </th>
            <th scope="col" className={thClass}>
              Versión
            </th>
            <th scope="col" className={thClass}>
              Fecha
            </th>
            <th scope="col" className={`${thClass} ${numericClass}`}>
              Índice
            </th>
            <th scope="col" className={thClass}>
              Estado
            </th>
          </tr>
        </thead>
        <tbody>
          {visible.map((work) => (
            <tr key={work.analysisId} className="hover:bg-canvas-soft">
              <td className={tdClass}>
                <Link href={workHref(work)} className="font-medium hover:text-accent-text">
                  {work.fileName}
                </Link>
              </td>
              <td className={tdClass}>v{work.version}</td>
              <td className={tdClass}>{work.date}</td>
              <td className={`${tdClass} ${numericClass}`}>{work.index ?? "—"}</td>
              <td
                className={`${tdClass} ${
                  work.status === "listo"
                    ? "text-verdict-verified-text"
                    : "text-verdict-discrepancy-text"
                }`}
              >
                {work.status === "listo" ? "Listo" : "En proceso"}
              </td>
            </tr>
          ))}
          {visible.length === 0 ? (
            <tr>
              <td colSpan={5} className={`${tdClass} text-body`}>
                Ningún trabajo coincide con la búsqueda.
              </td>
            </tr>
          ) : null}
        </tbody>
      </DataTable>
    </div>
  );
}

/** Esqueleto de WorkHistory: buscador y tabla. */
export function WorkHistorySkeleton() {
  return (
    <div className="flex flex-col gap-4">
      <span className={SEARCH_CLASSES}>
        <SkeletonText textClass="text-small" widthClass="w-32" />
      </span>
      <DataTableSkeleton columns={5} rows={4} />
    </div>
  );
}
