"use client";

import { useEffect, useState } from "react";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { StatCard, StatRow, StatRowSkeleton } from "@/shared/components/ui/stat-card";
import { VerdictBreakdown } from "@/shared/components/ui/verdict-breakdown";
import { formatDecimal } from "@/shared/lib/format";
import { fieldLabel } from "@/shared/lib/reference-fields";
import { fetchStatistics, type StatisticsOutcome } from "../api";
import type { AdminStatistics, Statistics, StudentStatistics, TeacherStatistics } from "../types";

const NO_VALUE = "—";
const NO_ANALYSES = "Las estadísticas aparecerán cuando termine el primer análisis.";

function StudentCards({ statistics }: { statistics: StudentStatistics }) {
  const { works, references, averageIndex, mostDifferentField } = statistics;
  return (
    <StatRow>
      <StatCard value={String(works)} label="Trabajos analizados" />
      <StatCard value={String(references)} label="Referencias revisadas" />
      <StatCard
        value={averageIndex === null ? NO_VALUE : formatDecimal(averageIndex, 1)}
        label="Índice de veracidad promedio"
      />
      <StatCard
        value={mostDifferentField ? fieldLabel(mostDifferentField) : NO_VALUE}
        label="Campo con más diferencias"
      />
    </StatRow>
  );
}

function TeacherCards({ statistics }: { statistics: TeacherStatistics }) {
  return (
    <StatRow>
      <StatCard value={String(statistics.batches)} label="Lotes" />
      <StatCard value={String(statistics.works)} label="Trabajos analizados" />
      <StatCard value={String(statistics.references)} label="Referencias" />
      <StatCard value={String(statistics.highRiskWorks)} label="De riesgo alto" tone="danger" />
    </StatRow>
  );
}

function AdminCards({ statistics }: { statistics: AdminStatistics }) {
  const { users, documents, references, queryErrors } = statistics;
  return (
    <>
      <StatRow>
        <StatCard value={String(users.estudiante)} label="Estudiantes" />
        <StatCard value={String(users.docente)} label="Docentes" />
        <StatCard value={String(users.admin)} label="Administradores" />
      </StatRow>
      <StatRow>
        <StatCard value={String(documents)} label="Documentos analizados" />
        <StatCard value={String(references)} label="Referencias procesadas" />
        <StatCard value={String(queryErrors)} label="Errores de consulta a las fuentes" />
      </StatRow>
    </>
  );
}

function RoleCards({ statistics }: { statistics: Statistics }) {
  if (statistics.role === "estudiante") return <StudentCards statistics={statistics} />;
  if (statistics.role === "docente") return <TeacherCards statistics={statistics} />;
  return <AdminCards statistics={statistics} />;
}

const VERDICT_TITLES: Record<Statistics["role"], string> = {
  estudiante: "Veredictos acumulados",
  docente: "Veredictos de tus lotes",
  admin: "Veredictos globales",
};

/** Las cifras del rol y sus veredictos (HU-18). */
export function StatisticsView({ statistics }: { statistics: Statistics }) {
  return (
    <div className="flex flex-col gap-4">
      <RoleCards statistics={statistics} />
      {statistics.references > 0 ? (
        <section
          aria-labelledby="titulo-veredictos-rol"
          className="flex flex-col gap-3 rounded-panel border border-hairline bg-canvas px-5 py-4"
        >
          <h2
            id="titulo-veredictos-rol"
            className="text-small font-semibold tracking-normal text-ink"
          >
            {VERDICT_TITLES[statistics.role]}
          </h2>
          <VerdictBreakdown counts={statistics.counts} total={statistics.references} />
          {statistics.queryErrors > 0 && statistics.role !== "admin" ? (
            <p className="text-small">
              {statistics.queryErrors === 1
                ? "1 referencia no se pudo verificar porque una fuente no respondió."
                : `${statistics.queryErrors} referencias no se pudieron verificar porque una fuente no respondió.`}
            </p>
          ) : null}
        </section>
      ) : (
        <p className="text-small">{NO_ANALYSES}</p>
      )}
    </div>
  );
}

/** Esqueleto de las cifras, con la misma cantidad de tarjetas de la pantalla. */
export function StatisticsSkeleton({ rows = 1, cards = 4 }: { rows?: number; cards?: number }) {
  return (
    <div className="flex flex-col gap-4">
      {Array.from({ length: rows }, (_, row) => (
        <StatRowSkeleton key={row} count={cards} />
      ))}
      <Skeleton className="h-40 w-full rounded-panel" />
    </div>
  );
}

type StatisticsLoaderProps = {
  /**
   * Es un complemento del inicio: mientras carga, si falla o si aún no hay análisis,
   * no ocupa lugar. Así el estudiante nuevo solo ve la subida de su trabajo.
   */
  quiet?: boolean;
  rows?: number;
  cards?: number;
};

/** Pide las cifras del rol de la sesión y muestra la carga, los datos o el motivo. */
export function StatisticsLoader({ quiet = false, rows, cards }: StatisticsLoaderProps) {
  const [outcome, setOutcome] = useState<StatisticsOutcome | null>(null);
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    let active = true;
    fetchStatistics(() => {
      if (active) setSlow(true);
    }).then((result) => {
      if (active) setOutcome(result);
    });
    return () => {
      active = false;
    };
  }, []);

  if (!outcome) {
    if (quiet) return null;
    return (
      <div className="flex flex-col gap-4">
        <p role="status" className="sr-only">
          Cargando las estadísticas…
        </p>
        {slow ? (
          <p className="text-small">
            Iniciando el motor de análisis; este proceso puede tardar hasta un minuto.
          </p>
        ) : null}
        <StatisticsSkeleton rows={rows} cards={cards} />
      </div>
    );
  }
  if (outcome.kind === "error") {
    if (quiet) return null;
    return (
      <p role="alert" className="text-small text-verdict-contradiction-text">
        {outcome.message}
      </p>
    );
  }
  if (quiet && outcome.statistics.references === 0) return null;
  return <StatisticsView statistics={outcome.statistics} />;
}
