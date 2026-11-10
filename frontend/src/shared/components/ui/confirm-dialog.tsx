"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { buttonStyles } from "./button-styles";

type ConfirmDialogProps = {
  title: string;
  children: ReactNode;
  confirmLabel: string;
  /** La acción está en curso: el diálogo no se puede cerrar ni confirmar otra vez. */
  busy?: boolean;
  /** Motivo por el que la acción no se pudo completar. */
  error?: string | null;
  onConfirm: () => void;
  onCancel: () => void;
};

/**
 * Pide confirmar una acción antes de aplicarla. Se monta solo mientras hace falta;
 * el elemento dialog atrapa el foco y se cierra con Esc.
 */
export function ConfirmDialog({
  title,
  children,
  confirmLabel,
  busy = false,
  error = null,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    dialogRef.current?.showModal();
  }, []);

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby="titulo-confirmacion"
      onCancel={(event) => {
        // Esc: el estado lo maneja React, no el navegador.
        event.preventDefault();
        if (!busy) onCancel();
      }}
      className="m-auto w-11/12 max-w-md flex-col gap-4 rounded-panel border border-hairline bg-canvas p-6 text-ink backdrop:bg-ink/40 open:flex"
    >
      <h2 id="titulo-confirmacion" className="text-title font-semibold tracking-normal">
        {title}
      </h2>
      <div className="text-small">{children}</div>
      {error ? (
        <p role="alert" className="text-small text-verdict-contradiction-text">
          {error}
        </p>
      ) : null}
      <div className="flex flex-col-reverse gap-2 md:flex-row md:justify-end">
        <button
          type="button"
          onClick={onCancel}
          disabled={busy}
          className={buttonStyles({ variant: "secondary" })}
        >
          Cancelar
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={busy}
          aria-busy={busy}
          className={buttonStyles()}
        >
          {confirmLabel}
        </button>
      </div>
    </dialog>
  );
}
