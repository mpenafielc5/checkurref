import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { Eyebrow } from "./ui/eyebrow";
import { Skeleton, SkeletonText } from "./ui/skeleton";

type BackLink = {
  href: string;
  /** Nombre de la pantalla de destino, por ejemplo "Mis trabajos". */
  label: string;
};

type PageSectionProps = {
  title: string;
  eyebrow?: string;
  description?: string;
  actions?: ReactNode;
  /** Enlace a la pantalla de nivel superior, en las pantallas de detalle. */
  back?: BackLink;
  children?: ReactNode;
};

const SECTION_CLASSES =
  "mx-auto flex w-full max-w-content flex-col gap-6 px-4 py-6 md:px-8 md:py-10";
const HEADER_CLASSES = "flex w-full flex-col gap-4 md:flex-row md:items-center md:justify-between";
const TITLE_TEXT = "text-display-sm md:text-display-md";
const BACK_CLASSES = "mb-2 flex items-center gap-1.5 self-start text-small";

/** Encabezado y contenedor estándar de una pantalla interna. */
export function PageSection({
  title,
  eyebrow,
  description,
  actions,
  back,
  children,
}: PageSectionProps) {
  return (
    <section aria-labelledby="titulo-pagina" className={SECTION_CLASSES}>
      <header className={HEADER_CLASSES}>
        <div className="flex flex-col gap-2">
          {back ? (
            <Link href={back.href} className={`${BACK_CLASSES} text-body hover:text-ink`}>
              <ArrowLeft aria-hidden="true" className="size-4" />
              Volver a {back.label}
            </Link>
          ) : null}
          {eyebrow ? <Eyebrow>{eyebrow}</Eyebrow> : null}
          <h1 id="titulo-pagina" className={TITLE_TEXT}>
            {title}
          </h1>
          {description ? <p className="max-w-2xl">{description}</p> : null}
        </div>
        {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
      </header>
      {children}
    </section>
  );
}

type PageSectionSkeletonProps = {
  /** La pantalla real muestra una descripción bajo el título. */
  description?: boolean;
  /** La pantalla real tiene un botón en la cabecera. */
  action?: boolean;
  /** La pantalla real tiene el enlace "Volver a…". */
  back?: boolean;
  /** Esqueleto del contenido; si falta, un bloque genérico. */
  children?: ReactNode;
};

/**
 * Esqueleto de PageSection mientras se verifica la sesión: misma cabecera y
 * mismos espacios, para que la pantalla no salte al aparecer el contenido.
 */
export function PageSectionSkeleton({
  description = false,
  action = false,
  back = false,
  children,
}: PageSectionSkeletonProps) {
  return (
    <section aria-busy="true" className={SECTION_CLASSES}>
      <p role="status" className="sr-only">
        Cargando…
      </p>
      <div className={HEADER_CLASSES}>
        <div className="flex flex-1 flex-col gap-2">
          {back ? (
            <span className={BACK_CLASSES}>
              <SkeletonText widthClass="w-32" />
            </span>
          ) : null}
          <SkeletonText textClass="font-mono text-caption" widthClass="w-24" />
          <SkeletonText textClass={`${TITLE_TEXT} leading-display`} widthClass="w-72 max-w-full" />
          {description ? <SkeletonText widthClass="w-full max-w-xl" /> : null}
        </div>
        {action ? <Skeleton className="h-control w-44 rounded-pill" /> : null}
      </div>
      {children ?? <Skeleton className="h-40 w-full rounded-card" />}
    </section>
  );
}
