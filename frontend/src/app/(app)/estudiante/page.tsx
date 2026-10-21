import { RolePage } from "@/features/auth/components/role-page";
import { RecentWorks } from "@/features/documents/components/recent-works";
import { SAMPLE_RECENT_WORKS } from "@/features/documents/sample-data";
import { PageSection } from "@/shared/components/page-section";
import { PdfDropzone } from "@/shared/components/pdf-dropzone";
import { SampleDataNotice } from "@/shared/components/ui/sample-data-notice";

/** Inicio del estudiante y subida del trabajo (maqueta 10). */
export default function StudentHomePage() {
  return (
    <RolePage allow={["estudiante"]}>
      <PageSection eyebrow="Estudiante" title="Revisa tus referencias antes de entregar">
        <PdfDropzone
          title="Arrastra aquí el PDF de tu trabajo"
          hint="o haz clic para elegirlo · máx. 10 MB · APA o IEEE en español"
          pendingMessage="Archivo validado. El envío al análisis se conecta en la HU-04."
        />
        <SampleDataNotice story="la HU-07" />
        <RecentWorks works={SAMPLE_RECENT_WORKS} />
      </PageSection>
    </RolePage>
  );
}
