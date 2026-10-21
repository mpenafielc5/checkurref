import { Suspense, type ReactNode } from "react";
import { AppSidebar, AppSidebarSkeleton } from "./app-sidebar";

/**
 * Marco común de las pantallas internas: barra lateral y contenido.
 *
 * Cada sección (estudiante, docente, admin, ayuda) lo usa desde su propio
 * layout. Next.js no vuelve a renderizar un layout al navegar dentro de su
 * sección, pero sí al pasar a otra; así, si el rol cambia y RoleGuard envía al
 * usuario a la sección de su nuevo rol, la barra se vuelve a pedir con el menú
 * correcto en lugar de quedarse con el del rol anterior.
 */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-1 flex-col md:flex-row">
      <Suspense fallback={<AppSidebarSkeleton />}>
        <AppSidebar />
      </Suspense>
      <main className="flex min-w-0 flex-1 flex-col bg-surface">{children}</main>
    </div>
  );
}
