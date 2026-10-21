import { RolePage } from "@/features/auth/components/role-page";
import { HelpContent } from "@/features/help/components/help-content";

/** Ayuda dentro de la sección del estudiante (contenido en HelpContent). */
export default function StudentHelpPage() {
  return (
    <RolePage allow={["estudiante"]}>
      <HelpContent />
    </RolePage>
  );
}
