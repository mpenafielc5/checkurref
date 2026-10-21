import type { ReactNode } from "react";
import { Suspense } from "react";
import { AppSidebar, AppSidebarSkeleton } from "@/features/auth/components/app-sidebar";

/** Marco común de las pantallas internas (requieren sesión, ver proxy.ts). */
export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-1 flex-col md:flex-row">
      <Suspense fallback={<AppSidebarSkeleton />}>
        <AppSidebar />
      </Suspense>
      <main className="flex min-w-0 flex-1 flex-col bg-surface">{children}</main>
    </div>
  );
}
