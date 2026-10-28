"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { PdfDropzone } from "@/shared/components/pdf-dropzone";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { submitDocument, wakeApi } from "../api";
import { analysisHref } from "../upload-rules";

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
  const uploading = phase.kind === "uploading";

  useEffect(() => {
    wakeApi();
  }, []);

  async function handleSubmit() {
    if (!file) return;
    setPhase({ kind: "uploading", slow: false });
    const outcome = await submitDocument(file, () => setPhase({ kind: "uploading", slow: true }));
    if (outcome.kind === "created") {
      router.push(analysisHref(outcome.analysisId, false));
    } else if (outcome.kind === "duplicate") {
      setPhase({ kind: "duplicate", analysisId: outcome.analysisId, finished: outcome.finished });
    } else {
      setPhase({ kind: "error", message: outcome.message });
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <PdfDropzone
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
        {phase.kind === "uploading" && phase.slow ? (
          <p className="text-small">
            Iniciando el motor de análisis; este proceso puede tardar hasta un minuto.
          </p>
        ) : null}
        {phase.kind === "error" ? (
          <p role="alert" className="text-small text-verdict-contradiction-text">
            {phase.message}
          </p>
        ) : null}
        {phase.kind === "duplicate" ? (
          <p className="text-small">
            Este PDF ya fue subido anteriormente; no se procesará de nuevo.{" "}
            <Link
              href={analysisHref(phase.analysisId, phase.finished)}
              className="font-semibold text-accent-text hover:underline"
            >
              {phase.finished ? "Abrir su informe" : "Ver su progreso"}
            </Link>
          </p>
        ) : null}
      </div>
    </div>
  );
}
