import Link from "next/link";
import { RolePage } from "@/features/auth/components/role-page";
import { WorkHistory, WorkHistorySkeleton } from "@/features/documents/components/work-history";
import { SAMPLE_VERSION_COMPARISON, SAMPLE_WORKS } from "@/features/documents/sample-data";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";
import { SampleDataNotice } from "@/shared/components/ui/sample-data-notice";
import { SkeletonText } from "@/shared/components/ui/skeleton";
import { StatCard, StatRow, StatRowSkeleton } from "@/shared/components/ui/stat-card";

const COMPARISON_CLASSES =
  "flex flex-col gap-3 rounded-panel border border-hairline bg-canvas px-5 py-4";

/** Mis trabajos: historial y versiones (maqueta 13). */
export default function StudentWorksPage() {
  const comparison = SAMPLE_VERSION_COMPARISON;

  return (
    <RolePage
      allow={["estudiante"]}
      skeleton={
        <PageSectionSkeleton>
          <SampleDataNotice story="la HU-07" />
          <WorkHistorySkeleton />
          <div className={COMPARISON_CLASSES}>
            <SkeletonText textClass="text-small" widthClass="w-48" />
            <StatRowSkeleton count={3} />
          </div>
        </PageSectionSkeleton>
      }
    >
      <PageSection eyebrow="Estudiante" title="Mis trabajos">
        <SampleDataNotice story="la HU-07" />
        <WorkHistory works={SAMPLE_WORKS} />

        <section aria-labelledby="titulo-comparacion" className={COMPARISON_CLASSES}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2
              id="titulo-comparacion"
              className="text-small font-semibold tracking-normal text-ink"
            >
              {comparison.title}
            </h2>
            <Link
              href={`/estudiante/trabajos/${comparison.latestAnalysisId}`}
              className="text-small font-medium text-accent-text hover:underline"
            >
              Ver informe v3 →
            </Link>
          </div>
          <StatRow>
            <StatCard
              value={`${comparison.indexBefore} → ${comparison.indexAfter}`}
              label="Índice de veracidad"
            />
            <StatCard value={comparison.resolved} label="Observaciones resueltas" tone="success" />
            <StatCard value={comparison.newFindings} label="Observación nueva" tone="warning" />
          </StatRow>
        </section>
      </PageSection>
    </RolePage>
  );
}
