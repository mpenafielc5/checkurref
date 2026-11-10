"use client";

import { FileWarning, FileX, Upload } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { EmptyState } from "@/shared/components/ui/empty-state";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { StatusChip } from "@/shared/components/ui/status-chip";
import { formatDate } from "@/shared/lib/format";
import { standardLabel } from "@/shared/lib/standards";
import { toSteps, verifyPercent, type AnalysisInfo } from "../progress";
import { useAnalysisProgress } from "../use-analysis-progress";
import { AnalysisProgress } from "./analysis-progress";
import { WakingNotice } from "@/shared/components/ui/notice";

const LIST_HREF = "/estudiante/trabajos";
const UPLOAD_HREF = "/estudiante";
const BACK = { href: LIST_HREF, label: "Mis trabajos" };

const backLink = (
  <Link href={LIST_HREF} className={buttonStyles({ variant: "secondary" })}>
    Volver a mis trabajos
  </Link>
);

function details(analysis: AnalysisInfo) {
  const pending = "Por detectar";
  return [
    {
      label: "Norma detectada",
      value: analysis.norm === null ? pending : (standardLabel(analysis.norm) ?? "No identificada"),
    },
    {
      label: "Referencias detectadas",
      value: analysis.totalReferences === null ? pending : String(analysis.totalReferences),
    },
    { label: "Fecha de subida", value: formatDate(analysis.createdAt) },
  ];
}

/**
 * Progreso en vivo de un análisis (HU-05, maqueta 11). Al completarse abre el
 * informe; si falla, muestra el motivo y lleva a subir el PDF corregido. El id sale de la dirección (useParams):
 * así la página no espera datos de la petición y se prerenderiza con su esqueleto.
 */
export function ProgressLoader() {
  const { analisisId: analysisId } = useParams<{ analisisId: string }>();
  const router = useRouter();
  const state = useAnalysisProgress(analysisId);
  const reportHref = `${LIST_HREF}/${analysisId}`;
  const completed = state.kind === "ready" && state.analysis.status === "completado";

  useEffect(() => {
    if (completed) router.replace(reportHref);
  }, [completed, reportHref, router]);

  if (state.kind === "loading") {
    return (
      <PageSectionSkeleton back description>
        <div className="flex flex-col gap-4">
          {state.slow ? <WakingNotice /> : null}
          <Skeleton className="h-40 w-full rounded-card" />
        </div>
      </PageSectionSkeleton>
    );
  }

  if (state.kind === "error") {
    return (
      <PageSection eyebrow="Análisis" title="Progreso del análisis" back={BACK}>
        <div role="alert">
          <EmptyState icon={FileX} title="No se pudo abrir el análisis" description={state.message}>
            {backLink}
          </EmptyState>
        </div>
      </PageSection>
    );
  }

  const { analysis } = state;
  const standard = standardLabel(analysis.norm);
  const steps = toSteps(analysis);
  const currentStep = steps.find((step) => step.state === "current");

  if (analysis.status === "error") {
    return (
      <PageSection eyebrow="Análisis no completado" title={analysis.fileName} back={BACK}>
        <div role="alert">
          <EmptyState
            icon={FileWarning}
            title="El análisis no pudo completarse"
            description={analysis.errorMessage ?? "Revisa el PDF y vuelve a subirlo."}
          >
            <Link href={UPLOAD_HREF} className={buttonStyles()}>
              <Upload aria-hidden="true" className="size-4" />
              Subir el PDF corregido
            </Link>
            {backLink}
          </EmptyState>
        </div>
      </PageSection>
    );
  }

  return (
    <PageSection
      eyebrow="Análisis en curso"
      title={analysis.fileName}
      description="El análisis continúa aunque salgas de esta pantalla; podrás consultarlo en Mis trabajos."
      back={BACK}
      actions={standard ? <StatusChip tone="neutral">{standard}</StatusChip> : null}
    >
      <p role="status" className="sr-only">
        {completed ? "Informe listo; abriendo el informe." : (currentStep?.title ?? "")}
      </p>
      <AnalysisProgress
        steps={steps}
        percent={analysis.status === "verificando" ? verifyPercent(analysis.progress) : null}
        details={details(analysis)}
      />
    </PageSection>
  );
}
