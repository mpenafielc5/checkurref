import { Plus } from "lucide-react";
import Link from "next/link";
import { RolePage } from "@/features/auth/components/role-page";
import { BatchList, BatchListSkeleton } from "@/features/batches/components/batch-list";
import { SAMPLE_BATCHES, SAMPLE_TEACHER_STATS } from "@/features/batches/sample-data";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { SampleDataNotice } from "@/shared/components/ui/sample-data-notice";
import { SkeletonText } from "@/shared/components/ui/skeleton";
import { StatCard, StatRow, StatRowSkeleton } from "@/shared/components/ui/stat-card";

/** Inicio del docente (maqueta 14). */
export default function TeacherHomePage() {
  const stats = SAMPLE_TEACHER_STATS;

  return (
    <RolePage
      allow={["docente"]}
      skeleton={
        <PageSectionSkeleton action>
          <SampleDataNotice story="la HU-08" />
          <StatRowSkeleton count={4} />
          <div className="flex flex-col gap-3">
            <SkeletonText textClass="text-small" widthClass="w-28" />
            <BatchListSkeleton rows={3} />
          </div>
        </PageSectionSkeleton>
      }
    >
      <PageSection
        eyebrow="Docente"
        title="Tus lotes de auditoría"
        actions={
          <Link href="/docente/lotes/nuevo" className={buttonStyles()}>
            <Plus aria-hidden="true" className="size-4" />
            Nueva auditoría
          </Link>
        }
      >
        <SampleDataNotice story="la HU-08" />
        <StatRow>
          <StatCard value={stats.activeBatches} label="Lotes activos" />
          <StatCard value={stats.works} label="Trabajos" />
          <StatCard value={stats.verified} label="Verificadas" tone="success" />
          <StatCard value={stats.alerts} label="Alertas" tone="danger" />
        </StatRow>
        <section aria-labelledby="titulo-lotes-recientes" className="flex flex-col gap-3">
          <h2
            id="titulo-lotes-recientes"
            className="text-small font-semibold tracking-normal text-ink"
          >
            Lotes recientes
          </h2>
          <BatchList batches={SAMPLE_BATCHES} />
        </section>
      </PageSection>
    </RolePage>
  );
}
