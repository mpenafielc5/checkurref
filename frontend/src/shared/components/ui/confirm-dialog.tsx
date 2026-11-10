"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { buttonStyles } from "./button-styles";
import { Notice } from "./notice";

/** El botón de confirmar anticipa el efecto: quitar acceso en rojo, devolverlo en verde. */
export type ConfirmTone = "default" | "danger" | "restore";

const CONFIRM_VARIANTS = {
  default: "primary",
  danger: "danger",
  restore: "restore",
} as const;

type ConfirmDialogProps = {
  title: string;
  children: ReactNode;
  confirmLabel: string;
  tone?: ConfirmTone;
  /** La acción está en curso: el diálogo no se puede cerrar ni confirmar otra vez. */
  busy?: boolean;
  /** Motivo por el que la acción no se pudo completar. */
  error?: string | null;
  onConfirm: () => void;
  onCancel: () => void;
};

/**
 * Pide confirmar una acción antes de aplicarla. Se monta solo mientras hace falta;
 * el elemento dialog atrapa el foco y se cierra con Esc. Alinea su texto a la
 * izquierda aunque se abra desde una celda alineada a la derecha.
 */
export function ConfirmDialog({
  title,
  children,
  confirmLabel,
  tone = "default",
  busy = false,
  error = null,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  const openerRef = useRef<Element | null>(null);

  useEffect(() => {
    // Al desmontarse, el navegador no devuelve el foco: se devuelve al botón que lo abrió.
    // Se guarda una sola vez porque en desarrollo React ejecuta este efecto dos veces.
    openerRef.current ??= document.activeElement;
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) dialog.showModal();
    return () => {
      if (openerRef.current instanceof HTMLElement) openerRef.current.focus();
    };
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
      className="m-auto w-11/12 max-w-md flex-col gap-4 overflow-y-auto overscroll-contain rounded-panel border border-hairline bg-canvas p-6 text-left text-ink backdrop:bg-ink/40 open:flex"
    >
      <h2 id="titulo-confirmacion" className="text-title font-semibold tracking-normal">
        {title}
      </h2>
      <div className="text-small">{children}</div>
      {error ? <Notice tone="error">{error}</Notice> : null}
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
          className={buttonStyles({ variant: CONFIRM_VARIANTS[tone] })}
        >
          {confirmLabel}
        </button>
      </div>
    </dialog>
  );
}
