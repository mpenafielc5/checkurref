import { FilePlus2 } from "lucide-react";
import Link from "next/link";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { MAX_FILES_PER_BATCH } from "@/shared/lib/pdf-rules";

type AddWorksLinkProps = {
  batchId: string;
  totalWorks: number;
  /** En el lote vacío es la acción principal. */
  primary?: boolean;
  /** Ancho dentro de la fila de acciones (por ejemplo, completo en el celular). */
  className?: string;
};

/**
 * Lleva a agregar trabajos a un lote que ya existe, por ejemplo un archivo
 * olvidado. Con el lote lleno se muestra desactivado y explica por qué.
 */
export function AddWorksLink({
  batchId,
  totalWorks,
  primary = false,
  className = "",
}: AddWorksLinkProps) {
  const icon = <FilePlus2 aria-hidden="true" className="size-4" />;
  if (totalWorks >= MAX_FILES_PER_BATCH) {
    return (
      <button
        type="button"
        disabled
        title={`El lote ya tiene el máximo de ${MAX_FILES_PER_BATCH} trabajos.`}
        className={`${buttonStyles({ variant: "secondary" })} ${className}`}
      >
        {icon}
        Agregar trabajos
      </button>
    );
  }
  return (
    <Link
      href={`/docente/lotes/${encodeURIComponent(batchId)}/agregar`}
      className={`${buttonStyles({ variant: primary ? "primary" : "secondary" })} ${className}`}
    >
      {icon}
      Agregar trabajos
    </Link>
  );
}
