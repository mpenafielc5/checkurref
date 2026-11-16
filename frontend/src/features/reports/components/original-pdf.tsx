"use client";

import { FileText } from "lucide-react";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { fetchOriginalPdfUrl } from "../api";

/**
 * El enlace del backend sirve una hora: se renueva antes, para que el botón y las
 * páginas sigan funcionando aunque el informe quede abierto mucho tiempo.
 */
export const RENEW_MS = 50 * 60 * 1000;

const OriginalPdfContext = createContext<string | null>(null);

/** Pide el enlace al PDF original del análisis y lo comparte con el informe. */
export function OriginalPdfProvider({
  analysisId,
  children,
}: {
  analysisId: string;
  children: ReactNode;
}) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = () => {
      fetchOriginalPdfUrl(analysisId).then((next) => {
        if (active && next) setUrl(next);
      });
    };
    load();
    const timer = setInterval(load, RENEW_MS);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [analysisId]);

  return <OriginalPdfContext.Provider value={url}>{children}</OriginalPdfContext.Provider>;
}

/** Abre el PDF que se subió en otra pestaña; no aparece si no hay enlace. */
export function OriginalPdfButton() {
  const url = useContext(OriginalPdfContext);
  if (!url) return null;
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={buttonStyles({ variant: "secondary" })}
    >
      <FileText aria-hidden="true" className="size-4" />
      Ver PDF original
    </a>
  );
}

/**
 * La página donde está la referencia. Con enlace, abre el PDF en esa página (los
 * visores de Chrome, Edge y Firefox respetan #page; Safari en el iPhone lo abre
 * desde el inicio); sin enlace, es solo texto.
 */
export function PageLink({ page }: { page: number }) {
  const url = useContext(OriginalPdfContext);
  if (!url) return <span className="text-body">Página {page}</span>;
  return (
    <a
      href={`${url}#page=${page}`}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`Página ${page}: abrir el PDF original en esa página, en otra pestaña`}
      className="text-accent-text underline hover:text-ink"
    >
      Página {page}
    </a>
  );
}
