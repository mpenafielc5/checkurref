"use client";

import { Pencil } from "lucide-react";
import { useState } from "react";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { ConfirmDialog } from "@/shared/components/ui/confirm-dialog";
import { updateBatch } from "../api";
import { MAX_NAME_LENGTH, MAX_PERIOD_LENGTH } from "../rules";
import type { BatchDetail } from "../types";

const INPUT_CLASSES =
  "h-input w-full rounded-control border border-hairline-strong bg-surface px-4 text-small text-ink outline-none focus:border-ink";

type EditBatchButtonProps = {
  batch: Pick<BatchDetail, "id" | "name" | "period">;
  onSaved: () => void;
  /** Ancho dentro de la fila de acciones. */
  className?: string;
};

/** Corrige el nombre o el periodo del lote; sus trabajos y resultados no cambian. */
export function EditBatchButton({ batch, onSaved, className = "" }: EditBatchButtonProps) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(batch.name);
  const [period, setPeriod] = useState(batch.period ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function openDialog() {
    setName(batch.name);
    setPeriod(batch.period ?? "");
    setError(null);
    setOpen(true);
  }

  async function handleSave() {
    const cleanName = name.trim();
    const cleanPeriod = period.trim();
    if (!cleanName || !cleanPeriod) {
      setError("Escribe el nombre y el periodo del lote.");
      return;
    }
    setBusy(true);
    setError(null);
    const outcome = await updateBatch(batch.id, cleanName, cleanPeriod);
    setBusy(false);
    if (outcome.kind === "updated") {
      setOpen(false);
      onSaved();
      return;
    }
    setError(outcome.message);
  }

  return (
    <>
      <button
        type="button"
        onClick={openDialog}
        className={`${buttonStyles({ variant: "secondary" })} ${className}`}
      >
        <Pencil aria-hidden="true" className="size-4" />
        Editar
      </button>
      {open ? (
        <ConfirmDialog
          title="Editar lote"
          confirmLabel={busy ? "Guardando…" : "Guardar cambios"}
          busy={busy}
          error={error}
          onConfirm={() => void handleSave()}
          onCancel={() => setOpen(false)}
        >
          <div className="flex flex-col gap-4">
            <label className="flex flex-col gap-1.5">
              Nombre del lote
              <input
                name="nombre"
                autoComplete="off"
                required
                maxLength={MAX_NAME_LENGTH}
                value={name}
                onChange={(event) => setName(event.target.value)}
                disabled={busy}
                className={INPUT_CLASSES}
              />
            </label>
            <label className="flex flex-col gap-1.5">
              Periodo
              <input
                name="periodo"
                autoComplete="off"
                required
                maxLength={MAX_PERIOD_LENGTH}
                value={period}
                onChange={(event) => setPeriod(event.target.value)}
                disabled={busy}
                className={INPUT_CLASSES}
              />
            </label>
          </div>
        </ConfirmDialog>
      ) : null}
    </>
  );
}
