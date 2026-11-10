"use client";

import { Check, Copy } from "lucide-react";
import { useEffect, useState } from "react";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import type { CorrectedReference } from "../types";
import { Notice } from "@/shared/components/ui/notice";

/** Tiempo que se muestra la confirmación "Copiada" (HU-19 CA03). */
export const COPIED_MS = 2_000;

type CopyStatus = "idle" | "copied" | "failed";

/**
 * Referencia corregida en APA 7 o IEEE (HU-19): vista previa con lo que cambió
 * resaltado y la opción de copiarla al portapapeles.
 */
export function CorrectedReferencePanel({ corrected }: { corrected: CorrectedReference }) {
  const [status, setStatus] = useState<CopyStatus>("idle");
  const hasChanges = corrected.segments.some((segment) => segment.changed);

  useEffect(() => {
    if (status !== "copied") return;
    const timer = setTimeout(() => setStatus("idle"), COPIED_MS);
    return () => clearTimeout(timer);
  }, [status]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(corrected.text);
      setStatus("copied");
    } catch {
      setStatus("failed");
    }
  }

  return (
    <section
      aria-label="Referencia corregida"
      className="flex flex-col gap-3 rounded-card bg-canvas px-4 py-3 text-small"
    >
      <p className="font-mono text-caption text-accent-text uppercase">Referencia corregida</p>
      <p className="wrap-anywhere text-ink">
        {corrected.segments.map((segment, index) => {
          const text = segment.italic ? <i>{segment.text}</i> : segment.text;
          return segment.changed ? (
            <mark
              key={index}
              className="rounded-row bg-verdict-verified-soft font-semibold text-verdict-verified-text"
            >
              {text}
            </mark>
          ) : (
            <span key={index}>{text}</span>
          );
        })}
      </p>
      {hasChanges ? (
        <p className="text-caption text-body">
          Resaltado: los datos que cambian respecto de tu referencia.
        </p>
      ) : null}
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" onClick={copy} className={buttonStyles({ variant: "secondary" })}>
          {status === "copied" ? (
            <Check aria-hidden="true" className="size-4" />
          ) : (
            <Copy aria-hidden="true" className="size-4" />
          )}
          {status === "copied" ? "Copiada" : "Copiar referencia corregida"}
        </button>
        <span aria-live="polite" className="sr-only">
          {status === "copied" ? "Referencia corregida copiada al portapapeles" : ""}
        </span>
        {status === "failed" ? (
          <Notice tone="error">
            No se pudo copiar. Selecciona el texto de la referencia y cópialo manualmente.
          </Notice>
        ) : null}
      </div>
    </section>
  );
}
