import { Suspense, type ReactNode } from "react";
import { PageSectionSkeleton } from "@/shared/components/page-section";
import type { UserRole } from "../types";
import { RoleGuard } from "./role-guard";

type RolePageProps = {
  allow: UserRole[];
  /** Esqueleto con la forma de la pantalla; si falta, uno genérico. */
  skeleton?: ReactNode;
  children: ReactNode;
};

/**
 * Envoltorio de cada pantalla interna: espera la sesión (Suspense) y solo
 * muestra el contenido a los roles permitidos.
 */
export function RolePage({ allow, skeleton = <PageSectionSkeleton />, children }: RolePageProps) {
  return (
    <Suspense fallback={skeleton}>
      <RoleGuard allow={allow}>{children}</RoleGuard>
    </Suspense>
  );
}
