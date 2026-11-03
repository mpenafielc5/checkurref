"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { fetchReport, type ReportOutcome } from "../api";
import { ReportView } from "./report-view";

type LoadState = { kind: "loading"; slow: boolean } | ReportOutcome;

type ReportLoaderProps = {
  /** Lista de trabajos de la que cuelga el informe: /{listHref}/{analisisId}. */
  listHref: string;
};

/**
 * Pide el informe a la API (HU-06) y muestra la carga, el informe o el motivo
 * por el que no está. El id sale de la dirección (useParams): así la página no
 * espera datos de la petición y se prerenderiza con su esqueleto.
 */
export function ReportLoader({ listHref }: ReportLoaderProps) {
  const { analisisId: analysisId } = useParams<{ analisisId: string }>();
  const [state, setState] = useState<LoadState>({ kind: "loading", slow: false });

  useEffect(() => {
    let active = true;
    const markSlow = () => {
      if (active)
        setState((current) => (current.kind === "loading" ? { ...current, slow: true } : current));
    };
    fetchReport(analysisId, markSlow).then((outcome) => {
      if (active) setState(outcome);
    });
    return () => {
      active = false;
    };
  }, [analysisId]);

  if (state.kind === "ready") return <ReportView report={state.report} />;

  return (
    <div aria-live="polite" className="flex flex-col gap-4">
      {state.kind === "loading" ? (
        <>
          <p className="sr-only">Cargando el informe…</p>
          {state.slow ? (
            <p className="text-small">
              Iniciando el motor de análisis; este proceso puede tardar hasta un minuto.
            </p>
          ) : null}
          <Skeleton className="h-8 w-2/3 rounded-control" />
          <Skeleton className="h-32 w-full rounded-panel" />
          <Skeleton className="h-24 w-full rounded-panel" />
        </>
      ) : null}

      {state.kind === "in_progress" ? (
        <div className="flex flex-col items-start gap-3">
          <p className="text-body">
            El análisis aún no termina. El informe estará disponible cuando se complete.
          </p>
          <Link
            href={`${listHref}/${analysisId}/progreso`}
            className={buttonStyles({ variant: "primary" })}
          >
            Ver el progreso
          </Link>
        </div>
      ) : null}

      {state.kind === "error" ? (
        <div className="flex flex-col items-start gap-3">
          <p role="alert" className="text-small text-verdict-contradiction-text">
            {state.message}
          </p>
          <Link href={listHref} className={buttonStyles({ variant: "secondary" })}>
            Volver a mis trabajos
          </Link>
        </div>
      ) : null}
    </div>
  );
}
