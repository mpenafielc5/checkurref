import { Plus } from "lucide-react";
import Link from "next/link";
import { RolePage } from "@/features/auth/components/role-page";
import { BatchListSkeleton } from "@/features/batches/components/batch-list";
import { RecentBatchesLoader } from "@/features/batches/components/batches-loader";
import {
  StatisticsLoader,
  StatisticsSkeleton,
} from "@/features/stats/components/statistics-loader";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { SkeletonText } from "@/shared/components/ui/skeleton";

/** Inicio del docente (maqueta 14, HU-18). */
export default function TeacherHomePage() {
  return (
    <RolePage
      allow={["docente"]}
      skeleton={
        <PageSectionSkeleton action>
          <StatisticsSkeleton />
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
        <StatisticsLoader />
        <section aria-labelledby="titulo-lotes-recientes" className="flex flex-col gap-3">
          <h2
            id="titulo-lotes-recientes"
            className="text-small font-semibold tracking-normal text-ink"
          >
            Lotes recientes
          </h2>
          <RecentBatchesLoader />
        </section>
      </PageSection>
    </RolePage>
  );
}
