"use client";

import { FileText, Search, SearchX, Upload } from "lucide-react";
import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import {
  cardClass,
  cardListClass,
  DataTable,
  DataTableSkeleton,
  numericClass,
  tableHeadClass,
  tdClass,
  thClass,
} from "@/shared/components/ui/data-table";
import { DeleteWorkButton } from "@/shared/components/delete-work-button";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { EmptyState } from "@/shared/components/ui/empty-state";
import { SkeletonText } from "@/shared/components/ui/skeleton";
import { workHref } from "../history";
import type { Work } from "../types";
import { WorkStatusChip } from "./work-status-chip";
import { formatIndex } from "@/shared/lib/format";

const SEARCH_CLASSES =
  "flex h-input w-full items-center gap-2 rounded-control border border-hairline-strong bg-canvas px-4 md:max-w-xs";

const STATUS_LABELS: Record<Work["status"], { label: string; className: string }> = {
  listo: { label: "Listo", className: "text-verdict-verified-text" },
  en_proceso: { label: "En proceso", className: "text-verdict-discrepancy-text" },
  error: { label: "Error", className: "text-verdict-contradiction-text" },
};

/** Pausa tras la última tecla antes de buscar: no se consulta la API en cada letra. */
export const SEARCH_DELAY_MS = 300;

type WorkSearchProps = {
  /** Búsqueda aplicada (viaja en la dirección); "" sin búsqueda. */
  search: string;
  onSearch: (search: string) => void;
};

/**
 * Buscador por nombre (maqueta 13): busca mientras se escribe, tras una pausa
 * breve; Enter aplica la búsqueda al instante. Queda fuera de la lista para no
 * perder el foco mientras llegan los resultados.
 */
export function WorkSearch({ search, onSearch }: WorkSearchProps) {
  const [query, setQuery] = useState(search);

  useEffect(() => {
    const value = query.trim();
    if (value === search) return;
    const timer = setTimeout(() => onSearch(value), SEARCH_DELAY_MS);
    return () => clearTimeout(timer);
  }, [query, search, onSearch]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (query.trim() !== search) onSearch(query.trim());
  }

  return (
    <form role="search" onSubmit={submit} className="flex">
      <label className={SEARCH_CLASSES}>
        <Search aria-hidden="true" className="size-5 text-muted" />
        <span className="sr-only">Buscar trabajo por nombre</span>
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Buscar trabajo…"
          className="w-full bg-transparent text-small text-ink outline-none placeholder:text-muted"
        />
      </label>
    </form>
  );
}

type WorkHistoryProps = {
  works: Work[];
  /** Hay una búsqueda aplicada: cambia el mensaje de la lista vacía. */
  searching: boolean;
  /** Tras eliminar un trabajo, la lista se vuelve a pedir. */
  onDeleted?: () => void;
};

/**
 * Historial de trabajos (maqueta 13). Cada archivo es un trabajo independiente,
 * del más reciente al más antiguo. La búsqueda la hace la API, sobre todos los
 * trabajos y no solo la página visible.
 */
export function WorkHistory({ works, searching, onDeleted }: WorkHistoryProps) {
  // Un análisis en curso todavía escribe sus resultados: se elimina cuando termina.
  const deletable = (work: Work) => onDeleted !== undefined && work.status !== "en_proceso";

  if (works.length === 0) {
    return searching ? (
      <EmptyState
        icon={SearchX}
        title="Sin resultados"
        description="Ningún trabajo coincide con la búsqueda."
      />
    ) : (
      <EmptyState
        icon={FileText}
        title="Aún no has subido trabajos"
        description="Sube el PDF de tu trabajo para revisar sus referencias."
      >
        <Link href="/estudiante" className={buttonStyles()}>
          <Upload aria-hidden="true" className="size-4" />
          Subir un trabajo
        </Link>
      </EmptyState>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <ul className={cardListClass}>
        {works.map((work) => (
          <li
            key={work.analysisId}
            className={`${cardClass} flex-row items-start has-[a:hover]:border-hairline-strong`}
          >
            <Link href={workHref(work)} className="flex min-w-0 flex-1 flex-col gap-2">
              <span className="font-semibold wrap-anywhere text-ink">{work.fileName}</span>
              <span className="flex items-center justify-between gap-3">
                <span className="text-small">{work.date}</span>
                <WorkStatusChip work={work} />
              </span>
            </Link>
            {deletable(work) && onDeleted ? (
              <DeleteWorkButton
                analysisId={work.analysisId}
                fileName={work.fileName}
                onDeleted={onDeleted}
              />
            ) : null}
          </li>
        ))}
      </ul>

      <DataTable caption="Historial de trabajos" cardsOnMobile>
        <thead className={tableHeadClass}>
          <tr>
            <th scope="col" className={thClass}>
              Archivo
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
            {onDeleted ? (
              <th scope="col" className={thClass}>
                <span className="sr-only">Acciones</span>
              </th>
            ) : null}
          </tr>
        </thead>
        <tbody>
          {works.map((work) => (
            <tr key={work.analysisId} className="hover:bg-canvas-soft">
              <td className={tdClass}>
                <Link
                  href={workHref(work)}
                  className="font-medium wrap-anywhere hover:text-accent-text"
                >
                  {work.fileName}
                </Link>
              </td>
              <td className={tdClass}>{work.date}</td>
              <td className={`${tdClass} ${numericClass}`}>
                {work.index === null ? "—" : formatIndex(work.index)}
              </td>
              <td className={`${tdClass} ${STATUS_LABELS[work.status].className}`}>
                {STATUS_LABELS[work.status].label}
              </td>
              {onDeleted ? (
                <td className={`${tdClass} py-1 text-right`}>
                  {deletable(work) ? (
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
    </div>
  );
}

/** Esqueleto de la lista: tarjetas en el celular, tabla desde md. */
export function WorkListSkeleton() {
  return <DataTableSkeleton columns={4} rows={4} cardsOnMobile />;
}

/** Esqueleto de la pantalla: buscador y lista. */
export function WorkHistorySkeleton() {
  return (
    <div className="flex flex-col gap-4">
      <span className={SEARCH_CLASSES}>
        <SkeletonText textClass="text-small" widthClass="w-32" />
      </span>
      <WorkListSkeleton />
    </div>
  );
}
