import { Plus } from "lucide-react";
import Link from "next/link";
import { RolePage } from "@/features/auth/components/role-page";
import { BatchListSkeleton } from "@/features/batches/components/batch-list";
import { BatchesLoader } from "@/features/batches/components/batches-loader";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";
import { buttonStyles } from "@/shared/components/ui/button-styles";

/** Lista completa de lotes del docente. */
export default function TeacherBatchesPage() {
  return (
    <RolePage
      allow={["docente"]}
      skeleton={
        <PageSectionSkeleton description action>
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
        <BatchesLoader />
      </PageSection>
    </RolePage>
  );
}
