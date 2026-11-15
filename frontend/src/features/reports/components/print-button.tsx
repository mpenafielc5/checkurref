"use client";

import { Printer } from "lucide-react";
import { buttonStyles } from "@/shared/components/ui/button-styles";

/** Abre el diálogo de impresión, que también permite guardar el informe en PDF (HU-15). */
export function PrintButton() {
  return (
    <button
      type="button"
      onClick={() => window.print()}
      className={buttonStyles({ variant: "secondary" })}
    >
      <Printer aria-hidden="true" className="size-4" />
      Exportar PDF
    </button>
  );
}
