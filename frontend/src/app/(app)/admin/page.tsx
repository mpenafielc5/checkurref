import { FlaskConical, Users } from "lucide-react";
import Link from "next/link";
import { SAMPLE_ADMIN_STATS } from "@/features/admin/sample-data";
import { RolePage } from "@/features/auth/components/role-page";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";
import { SampleDataNotice } from "@/shared/components/ui/sample-data-notice";
import { Skeleton, SkeletonText } from "@/shared/components/ui/skeleton";
import { StatCard, StatRow, StatRowSkeleton } from "@/shared/components/ui/stat-card";

const SHORTCUTS = [
  {
    href: "/admin/usuarios",
    title: "Usuarios",
    description: "Asigna el rol de docente al personal verificado.",
    Icon: Users,
  },
  {
    href: "/admin/laboratorio",
    title: "Laboratorio",
    description: "Compara AnyStyle y spaCy, y ejecuta el benchmark.",
    Icon: FlaskConical,
  },
];

/** Inicio del administrador. */
export default function AdminHomePage() {
  const stats = SAMPLE_ADMIN_STATS;

  return (
    <RolePage
      allow={["admin"]}
      skeleton={
        <PageSectionSkeleton>
          <SampleDataNotice story="la HU-11 y la HU-12" />
          <StatRowSkeleton count={4} />
          <div className="flex flex-col gap-4 md:flex-row">
            {SHORTCUTS.map(({ href }) => (
              <div
                key={href}
                className="flex flex-1 items-start gap-4 rounded-card border border-hairline bg-canvas px-5 py-4"
              >
                <Skeleton className="size-6 shrink-0 rounded-row" />
                <span className="flex flex-1 flex-col gap-1">
                  <SkeletonText widthClass="w-24" />
                  <SkeletonText textClass="text-small" />
                </span>
              </div>
            ))}
          </div>
        </PageSectionSkeleton>
      }
    >
      <PageSection eyebrow="Administración" title="Inicio">
        <SampleDataNotice story="la HU-11 y la HU-12" />
        <StatRow>
          <StatCard value={stats.users} label="Usuarios" />
          <StatCard value={stats.analysesToday} label="Análisis hoy" />
          <StatCard value={stats.goldSet} label="Referencias en el estándar de oro" />
          <StatCard value={stats.lastBenchmark} label="Último benchmark" />
        </StatRow>
        <ul className="flex flex-col gap-4 md:flex-row">
          {SHORTCUTS.map(({ href, title, description, Icon }) => (
            <li key={href} className="flex flex-1">
              <Link
                href={href}
                className="flex w-full items-start gap-4 rounded-card border border-hairline bg-canvas px-5 py-4 hover:border-hairline-strong"
              >
                <Icon aria-hidden="true" className="size-6 shrink-0 text-primary" />
                <span className="flex flex-col gap-1">
                  <span className="font-semibold text-ink">{title}</span>
                  <span className="text-small">{description}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </PageSection>
    </RolePage>
  );
}
