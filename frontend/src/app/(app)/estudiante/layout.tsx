import type { ReactNode } from "react";
import { AppShell } from "@/features/auth/components/app-shell";

/** Marco de las pantallas del estudiante (ver AppShell). */
export default function StudentLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
