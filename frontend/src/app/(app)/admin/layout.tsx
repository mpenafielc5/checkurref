import type { ReactNode } from "react";
import { AppShell } from "@/features/auth/components/app-shell";

/** Marco de las pantallas del administrador (ver AppShell). */
export default function AdminLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
