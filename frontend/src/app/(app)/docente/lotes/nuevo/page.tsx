import { RolePage } from "@/features/auth/components/role-page";
import { NewBatchForm } from "@/features/batches/components/new-batch-form";
import { SAMPLE_NEW_BATCH_UPLOADS } from "@/features/batches/sample-data";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";
import { SampleDataNotice } from "@/shared/components/ui/sample-data-notice";

/** Nueva auditoría por lote (maqueta 15). */
export default function NewBatchPage() {
  return (
    <RolePage allow={["docente"]} skeleton={<PageSectionSkeleton back />}>
      <PageSection
        eyebrow="Docente"
        title="Nueva auditoría por lote"
        back={{ href: "/docente/lotes", label: "Lotes" }}
      >
        <SampleDataNotice story="la HU-08" />
        <NewBatchForm batchId="met-5b" uploads={SAMPLE_NEW_BATCH_UPLOADS} />
      </PageSection>
    </RolePage>
  );
}
