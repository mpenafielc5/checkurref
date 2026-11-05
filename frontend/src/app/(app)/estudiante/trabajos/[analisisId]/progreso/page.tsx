import { RolePage } from "@/features/auth/components/role-page";
import { ProgressLoader } from "@/features/documents/components/progress-loader";
import { PageSectionSkeleton } from "@/shared/components/page-section";

/** Progreso del análisis, en vivo (maqueta 11, HU-05). */
export default function StudentProgressPage() {
  return (
    <RolePage allow={["estudiante"]} skeleton={<PageSectionSkeleton back description />}>
      <ProgressLoader />
    </RolePage>
  );
}
