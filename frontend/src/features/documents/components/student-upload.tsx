"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useLayoutEffect, useState } from "react";
import { PdfDropzone } from "@/shared/components/pdf-dropzone";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { submitDocument, wakeApi } from "../api";
import { analysisHref } from "../upload-rules";
import { Notice, WakingNotice } from "@/shared/components/ui/notice";

type Phase =
  | { kind: "idle" }
  | { kind: "uploading"; slow: boolean }
  | { kind: "error"; message: string }
  | { kind: "duplicate"; analysisId: string; finished: boolean };

/**
 * Subida del trabajo del estudiante (HU-04): elige el PDF y lo envía a
 * analizar; la norma (APA o IEEE) la detecta el análisis. Al cargar la
 * pantalla despierta al backend, que en el plan gratuito se duerme sin uso.
 */
export function StudentUpload() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  /** Cambiarla vuelve a montar la zona de subida, que guarda el archivo elegido. */
  const [dropzoneKey, setDropzoneKey] = useState(0);
  const uploading = phase.kind === "uploading";

  useEffect(() => {
    wakeApi();
  }, []);

  // Next.js oculta la página al navegar en lugar de desmontarla y conserva su estado.
  // Al volver al inicio, la subida debe empezar de cero y no quedarse en "Subiendo…".
  useLayoutEffect(() => {
    return () => {
      setFile(null);
      setPhase({ kind: "idle" });
      setDropzoneKey((key) => key + 1);
    };
  }, []);

  async function handleSubmit() {
    if (!file) return;
    setPhase({ kind: "uploading", slow: false });
    const outcome = await submitDocument(file, () => setPhase({ kind: "uploading", slow: true }));
    if (outcome.kind === "created") {
      router.push(analysisHref(outcome.analysisId, false));
    } else if (outcome.kind === "duplicate") {
      setPhase({ kind: "duplicate", analysisId: outcome.analysisId, finished: outcome.finished });
    } else if (outcome.rejected) {
      // La API revisó el PDF y no lo acepta: igual que un archivo inválido del navegador,
      // la zona queda vacía y el aviso dice cuál fue y por qué. Reenviarlo no serviría.
      setFile(null);
      setDropzoneKey((key) => key + 1);
      setPhase({ kind: "error", message: `${file.name}: ${outcome.message}` });
    } else {
      // Una falla de conexión o del servidor: el archivo sigue elegido para reintentar.
      setPhase({ kind: "error", message: outcome.message });
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <PdfDropzone
        key={dropzoneKey}
        title="Arrastra aquí el PDF de tu trabajo"
        hint="o haz clic para elegirlo · máx. 10 MB · APA o IEEE (detección automática)"
        disabled={uploading}
        onChange={(files) => {
          setFile(files[0] ?? null);
          setPhase({ kind: "idle" });
        }}
      >
        <button
          type="button"
          disabled={!file || uploading}
          aria-busy={uploading}
          onClick={handleSubmit}
          className={`${buttonStyles({ fullWidth: true })} md:w-auto`}
        >
          {uploading ? "Subiendo…" : "Analizar referencias"}
        </button>
      </PdfDropzone>

      <div aria-live="polite" className="flex flex-col text-center">
        {phase.kind === "uploading" && phase.slow ? <WakingNotice /> : null}
        {phase.kind === "error" ? <Notice tone="error">{phase.message}</Notice> : null}
        {phase.kind === "duplicate" ? (
          <Notice>
            Este PDF ya se analizó antes; no se procesa de nuevo.{" "}
            <Link
              href={analysisHref(phase.analysisId, phase.finished)}
              className="font-semibold text-accent-text hover:underline"
            >
              {phase.finished ? "Abrir su informe" : "Ver su progreso"}
            </Link>
          </Notice>
        ) : null}
      </div>
    </div>
  );
}
