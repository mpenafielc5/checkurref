import { RolePage } from "@/features/auth/components/role-page";
import { AnalysisProgress } from "@/features/documents/components/analysis-progress";
import { SAMPLE_PROGRESS } from "@/features/documents/sample-data";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";
import { SampleDataNotice } from "@/shared/components/ui/sample-data-notice";
import { StatusChip } from "@/shared/components/ui/status-chip";

/** Progreso del análisis, en vivo (maqueta 11). */
export default function StudentProgressPage() {
  const progress = SAMPLE_PROGRESS;

  return (
    <RolePage allow={["estudiante"]} skeleton={<PageSectionSkeleton back description />}>
      <PageSection
        eyebrow="Análisis en curso"
        title={progress.fileName}
        description="El análisis sigue aunque salgas de esta pantalla; lo encontrarás en Mis trabajos."
        back={{ href: "/estudiante/trabajos", label: "Mis trabajos" }}
        actions={<StatusChip tone="neutral">{progress.standard}</StatusChip>}
      >
        <SampleDataNotice story="la HU-05" />
        <AnalysisProgress
          steps={progress.steps}
          verified={progress.verified}
          total={progress.total}
          latest={progress.latest}
        />
      </PageSection>
    </RolePage>
  );
}
