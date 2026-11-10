"use client";

import { Trash2 } from "lucide-react";
import { useState } from "react";
import { ConfirmDialog } from "@/shared/components/ui/confirm-dialog";
import { deleteWork } from "@/shared/lib/work-deletion";

/** Ícono discreto en reposo; se pone rojo al pasar el cursor, como las demás acciones destructivas. */
const ICON_BUTTON =
  "inline-flex size-control shrink-0 touch-manipulation items-center justify-center rounded-pill text-body transition-colors hover:bg-danger hover:text-on-danger";

type DeleteWorkButtonProps = {
  analysisId: string;
  fileName: string;
  onDeleted: () => void;
};

/**
 * Elimina un trabajo con su PDF y su informe, después de confirmarlo. Se muestra
 * solo cuando el análisis terminó: uno en curso todavía escribe sus resultados.
 */
export function DeleteWorkButton({ analysisId, fileName, onDeleted }: DeleteWorkButtonProps) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleConfirm() {
    setBusy(true);
    setError(null);
    const outcome = await deleteWork(analysisId);
    setBusy(false);
    if (outcome.kind === "deleted") {
      setOpen(false);
      onDeleted();
      return;
    }
    setError(outcome.message);
  }

  return (
    <>
      <button
        type="button"
        aria-label={`Eliminar ${fileName}`}
        title="Eliminar trabajo"
        onClick={() => {
          setError(null);
          setOpen(true);
        }}
        className={ICON_BUTTON}
      >
        <Trash2 aria-hidden="true" className="size-5" />
      </button>
      {open ? (
        <ConfirmDialog
          title="¿Eliminar este trabajo?"
          confirmLabel={busy ? "Eliminando…" : "Eliminar trabajo"}
          tone="danger"
          busy={busy}
          error={error}
          onConfirm={() => void handleConfirm()}
          onCancel={() => setOpen(false)}
        >
          <p>Se eliminarán el PDF y su informe. Esta acción no se puede deshacer.</p>
          <p className="mt-1 text-caption wrap-anywhere text-muted">{fileName}</p>
        </ConfirmDialog>
      ) : null}
    </>
  );
}
