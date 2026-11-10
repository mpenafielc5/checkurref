"use client";

import { FileX, Hourglass } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { EmptyState } from "@/shared/components/ui/empty-state";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { fetchReport, type ReportOutcome } from "../api";
import { ReportView } from "./report-view";
import { WakingNotice } from "@/shared/components/ui/notice";

type LoadState = { kind: "loading"; slow: boolean } | ReportOutcome;

type ReportLoaderProps = {
  /** Lista de trabajos de la que cuelga el informe: /{listHref}/{analisisId}. */
  listHref: string;
  /** Texto del enlace de regreso a esa lista. */
  backLabel?: string;
  /** El rol tiene una pantalla de progreso; si no, un análisis en curso vuelve a la lista. */
  hasProgressPage?: boolean;
};

/**
 * Pide el informe a la API (HU-06) y muestra la carga, el informe o el motivo
 * por el que no está. El id sale de la dirección (useParams): así la página no
 * espera datos de la petición y se prerenderiza con su esqueleto. Un análisis en
 * curso lleva solo a su progreso, igual que el progreso lleva al informe al terminar.
 */
export function ReportLoader({
  listHref,
  backLabel = "Volver a mis trabajos",
  hasProgressPage = true,
}: ReportLoaderProps) {
  const { analisisId: analysisId } = useParams<{ analisisId: string }>();
  const router = useRouter();
  const [state, setState] = useState<LoadState>({ kind: "loading", slow: false });
  const redirecting = state.kind === "in_progress" && hasProgressPage;

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

  useEffect(() => {
    if (redirecting) router.replace(`${listHref}/${analysisId}/progreso`);
  }, [redirecting, router, listHref, analysisId]);

  if (state.kind === "ready") return <ReportView report={state.report} />;

  const backLink = (
    <Link href={listHref} className={buttonStyles({ variant: "secondary" })}>
      {backLabel}
    </Link>
  );

  return (
    <div aria-live="polite" className="flex flex-col gap-4">
      {state.kind === "loading" || redirecting ? (
        <>
          <p className="sr-only">
            {redirecting
              ? "El análisis aún no termina; abriendo su progreso…"
              : "Cargando el informe…"}
          </p>
          {state.kind === "loading" && state.slow ? <WakingNotice /> : null}
          <Skeleton className="h-8 w-2/3 rounded-control" />
          <Skeleton className="h-32 w-full rounded-panel" />
          <Skeleton className="h-24 w-full rounded-panel" />
        </>
      ) : null}

      {state.kind === "in_progress" && !hasProgressPage ? (
        <EmptyState
          icon={Hourglass}
          title="El análisis aún no termina"
          description="El informe estará disponible cuando se complete."
        >
          {backLink}
        </EmptyState>
      ) : null}

      {state.kind === "error" ? (
        <div role="alert">
          <EmptyState icon={FileX} title="No se pudo abrir el informe" description={state.message}>
            {backLink}
          </EmptyState>
        </div>
      ) : null}
    </div>
  );
}
