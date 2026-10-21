import { Plus } from "lucide-react";
import Link from "next/link";
import { RolePage } from "@/features/auth/components/role-page";
import { BatchList, BatchListSkeleton } from "@/features/batches/components/batch-list";
import { SAMPLE_BATCHES } from "@/features/batches/sample-data";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { SampleDataNotice } from "@/shared/components/ui/sample-data-notice";

/** Lista completa de lotes del docente. */
export default function TeacherBatchesPage() {
  return (
    <RolePage
      allow={["docente"]}
      skeleton={
        <PageSectionSkeleton description action>
          <SampleDataNotice story="la HU-08" />
          <BatchListSkeleton rows={3} />
        </PageSectionSkeleton>
      }
    >
      <PageSection
        eyebrow="Docente"
        title="Lotes"
        description="Cada lote agrupa los trabajos de un curso y una entrega."
        actions={
          <Link href="/docente/lotes/nuevo" className={buttonStyles()}>
            <Plus aria-hidden="true" className="size-4" />
            Nueva auditoría
          </Link>
        }
      >
        <SampleDataNotice story="la HU-08" />
        <BatchList batches={SAMPLE_BATCHES} />
      </PageSection>
    </RolePage>
  );
}
