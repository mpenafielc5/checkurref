/** Reglas de los archivos que se pueden subir (las mismas que aplica Storage). */

export const MAX_PDF_BYTES = 10 * 1024 * 1024;
export const MAX_FILES_PER_BATCH = 40;

type FileLike = { name: string; type: string; size: number };

export type PdfValidation = { ok: true } | { ok: false; reason: string };

export function validatePdfFile(file: FileLike): PdfValidation {
  const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  if (!isPdf) {
    return { ok: false, reason: "Solo se aceptan archivos PDF." };
  }
  if (file.size > MAX_PDF_BYTES) {
    return { ok: false, reason: "El archivo supera el máximo de 10 MB." };
  }
  if (file.size === 0) {
    return { ok: false, reason: "El archivo está vacío." };
  }
  return { ok: true };
}
