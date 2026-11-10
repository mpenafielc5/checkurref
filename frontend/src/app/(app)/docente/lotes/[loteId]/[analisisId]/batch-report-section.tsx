"use client";

import { useParams } from "next/navigation";
import { ReportLoader } from "@/features/reports/components/report-loader";
import { PageSection } from "@/shared/components/page-section";

/** El regreso depende del lote de la dirección; el informe es el mismo del estudiante. */
export function BatchReportSection() {
  const { loteId } = useParams<{ loteId: string }>();
  const dashboardHref = `/docente/lotes/${loteId}`;

  return (
    <PageSection
      eyebrow="Informe"
      title="Diagnóstico de veracidad"
      back={{ href: dashboardHref, label: "Tablero del lote" }}
    >
      <ReportLoader
        listHref={dashboardHref}
        backLabel="Volver al tablero del lote"
        hasProgressPage={false}
      />
    </PageSection>
  );
}
