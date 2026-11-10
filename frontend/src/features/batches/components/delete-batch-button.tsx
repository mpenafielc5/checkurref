"use client";

import { Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { ConfirmDialog } from "@/shared/components/ui/confirm-dialog";
import { deleteBatch } from "../api";
import type { BatchDetail } from "../types";

const LIST_HREF = "/docente/lotes";

/** Qué se pierde al eliminar el lote, en singular o plural. */
function lossMessage(count: number): string {
  if (count === 0) return "El lote no tiene trabajos. Esta acción no se puede deshacer.";
  if (count === 1) {
    return "Se eliminará su único trabajo, con su PDF y su informe. Esta acción no se puede deshacer.";
  }
  return `Se eliminarán sus ${count} trabajos, con sus PDF y sus informes. Esta acción no se puede deshacer.`;
}

type DeleteBatchButtonProps = {
  batch: Pick<BatchDetail, "id" | "name" | "totalWorks" | "inProgress">;
  /** Ancho dentro de la fila de acciones. */
  className?: string;
};

/**
 * Elimina el lote con todos sus trabajos, sus PDF y sus informes (HU-23). Mientras
 * algún trabajo se analiza no se puede: el análisis todavía escribe sus resultados.
 */
export function DeleteBatchButton({ batch, className = "" }: DeleteBatchButtonProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const analyzing = batch.inProgress > 0;

  async function handleConfirm() {
    setBusy(true);
    setError(null);
    const outcome = await deleteBatch(batch.id);
    if (outcome.kind === "deleted") {
      router.push(LIST_HREF);
      return;
    }
    setBusy(false);
    setError(outcome.message);
  }

  return (
    <>
      <button
        type="button"
        disabled={analyzing}
        title={analyzing ? "Podrás eliminar el lote cuando terminen sus análisis." : undefined}
        onClick={() => {
          setError(null);
          setOpen(true);
        }}
        className={`${buttonStyles({ variant: "dangerQuiet" })} ${className}`}
      >
        <Trash2 aria-hidden="true" className="size-4" />
        Eliminar lote
      </button>
      {open ? (
        <ConfirmDialog
          title="¿Eliminar este lote?"
          confirmLabel={busy ? "Eliminando…" : "Eliminar lote"}
          tone="danger"
          busy={busy}
          error={error}
          onConfirm={() => void handleConfirm()}
          onCancel={() => setOpen(false)}
        >
          <p>{lossMessage(batch.totalWorks)}</p>
          <p className="mt-1 text-caption wrap-anywhere text-muted">{batch.name}</p>
        </ConfirmDialog>
      ) : null}
    </>
  );
}
