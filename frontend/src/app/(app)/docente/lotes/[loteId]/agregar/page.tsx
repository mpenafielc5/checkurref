import { RolePage } from "@/features/auth/components/role-page";
import { AddWorksLoader } from "@/features/batches/components/add-works-form";
import { PageSectionSkeleton } from "@/shared/components/page-section";

/** Agregar trabajos a un lote que ya existe, por ejemplo un archivo olvidado. */
export default function AddWorksPage() {
  return (
    <RolePage allow={["docente"]} skeleton={<PageSectionSkeleton back />}>
      <AddWorksLoader />
    </RolePage>
  );
}
