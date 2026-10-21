import { RolePage } from "@/features/auth/components/role-page";
import { BatchRiskTable } from "@/features/batches/components/batch-risk-table";
import { SAMPLE_BATCH_DETAIL } from "@/features/batches/sample-data";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { SampleDataNotice } from "@/shared/components/ui/sample-data-notice";
import { StatCard, StatRow } from "@/shared/components/ui/stat-card";

/** Tablero del lote: trabajos ordenados por riesgo (maqueta 16). */
export default function BatchDashboardPage() {
  const batch = SAMPLE_BATCH_DETAIL;

  return (
    <RolePage allow={["docente"]} skeleton={<PageSectionSkeleton back action />}>
      <PageSection
        eyebrow="Tablero del lote"
        title={batch.name}
        back={{ href: "/docente/lotes", label: "Lotes" }}
        actions={
          <button type="button" disabled className={buttonStyles({ variant: "secondary" })}>
            Exportar CSV
          </button>
        }
      >
        <SampleDataNotice story="la HU-09" />
        <StatRow>
          <StatCard value={batch.stats.works} label="Trabajos" />
          <StatCard value={batch.stats.references} label="Referencias" />
          <StatCard value={batch.stats.verified} label="Verificadas" tone="success" />
          <StatCard value={batch.stats.alerts} label="Alertas" tone="danger" />
        </StatRow>
        <section aria-labelledby="titulo-riesgo" className="flex flex-col gap-3">
          <h2 id="titulo-riesgo" className="text-small font-semibold tracking-normal text-ink">
            Trabajos ordenados por riesgo
          </h2>
          <BatchRiskTable batchId={batch.id} works={batch.works} />
        </section>
      </PageSection>
    </RolePage>
  );
}
