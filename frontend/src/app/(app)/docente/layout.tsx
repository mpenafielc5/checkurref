import type { ReactNode } from "react";
import { AppShell } from "@/features/auth/components/app-shell";

/** Marco de las pantallas del docente (ver AppShell). */
export default function TeacherLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
