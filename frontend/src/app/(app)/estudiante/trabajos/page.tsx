import { Upload } from "lucide-react";
import Link from "next/link";
import { RolePage } from "@/features/auth/components/role-page";
import { WorkHistorySkeleton } from "@/features/documents/components/work-history";
import { WorkHistoryLoader } from "@/features/documents/components/work-history-loader";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";
import { buttonStyles } from "@/shared/components/ui/button-styles";

/**
 * Mis trabajos: historial sin versiones (maqueta 13, Asesoría 1, HU-07). Como Lotes
 * del docente, la cabecera lleva al inicio, donde se sube el PDF.
 */
export default function StudentWorksPage() {
  return (
    <RolePage
      allow={["estudiante"]}
      skeleton={
        <PageSectionSkeleton action>
          <WorkHistorySkeleton />
        </PageSectionSkeleton>
      }
    >
      <PageSection
        eyebrow="Estudiante"
        title="Mis trabajos"
        actions={
          <Link href="/estudiante" className={buttonStyles()}>
            <Upload aria-hidden="true" className="size-4" />
            Subir trabajo
          </Link>
        }
      >
        <WorkHistoryLoader />
      </PageSection>
    </RolePage>
  );
}
