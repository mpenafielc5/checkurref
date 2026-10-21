/*
 * Marcadores de carga. Reservan el alto y el ancho del contenido final para que
 * la página no salte cuando llegan los datos. Son decorativos (aria-hidden):
 * la pantalla que los usa anuncia la carga con un texto para lectores de
 * pantalla (ver PageSectionSkeleton).
 */

/** Bloque con pulso suave. Quien lo usa define su tamaño y su forma. */
export function Skeleton({ className = "" }: { className?: string }) {
  return <span aria-hidden="true" className={`flex animate-pulse bg-skeleton ${className}`} />;
}

type SkeletonTextProps = {
  /** Clases de tipografía del texto real (tamaño e interlineado). */
  textClass?: string;
  widthClass?: string;
};

/**
 * Una línea de texto: mide exactamente lo que una línea con `textClass` (1lh)
 * y dibuja una barra algo más baja, como la altura visible de las letras.
 */
export function SkeletonText({ textClass = "", widthClass = "w-full" }: SkeletonTextProps) {
  return (
    <span aria-hidden="true" className={`flex h-lh items-center ${textClass}`}>
      <Skeleton className={`h-3/5 rounded-row ${widthClass}`} />
    </span>
  );
}
