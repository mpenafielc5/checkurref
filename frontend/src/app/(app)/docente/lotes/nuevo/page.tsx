import { RolePage } from "@/features/auth/components/role-page";
import { NewBatchForm } from "@/features/batches/components/new-batch-form";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";

/** Nueva auditoría por lote (maqueta 15, HU-08). */
export default function NewBatchPage() {
  return (
    <RolePage allow={["docente"]} skeleton={<PageSectionSkeleton back />}>
      <PageSection
        eyebrow="Docente"
        title="Nueva auditoría por lote"
        back={{ href: "/docente/lotes", label: "Lotes" }}
      >
        <NewBatchForm />
      </PageSection>
    </RolePage>
  );
}
