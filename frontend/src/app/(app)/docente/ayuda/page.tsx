import { RolePage } from "@/features/auth/components/role-page";
import { HelpContent } from "@/features/help/components/help-content";

/** Ayuda dentro de la sección del docente (contenido en HelpContent). */
export default function TeacherHelpPage() {
  return (
    <RolePage allow={["docente"]}>
      <HelpContent />
    </RolePage>
  );
}
