import { describe, expect, it } from "vitest";
import { sendProgress, stateAfterUpload } from "./upload-progress";
import type { BatchUpload } from "./types";

function upload(key: string, state: BatchUpload["state"]): BatchUpload {
  return { key, file: new File(["%PDF-"], `${key}.pdf`), state };
}

describe("stateAfterUpload", () => {
  it("un archivo que la API rechaza queda rechazado, sin reintento", () => {
    const reason = "No se encontró la sección de referencias.";
    expect(stateAfterUpload({ kind: "error", message: reason, rejected: true })).toEqual({
      kind: "rechazado",
      reason,
      byApi: true,
    });
  });

  it("una falla de conexión o del servidor se puede reintentar", () => {
    expect(stateAfterUpload({ kind: "error", message: "Sin conexión." })).toEqual({
      kind: "fallo_subida",
      reason: "Sin conexión.",
    });
  });

  it("el total del envío no baja cuando la API rechaza un archivo", () => {
    const uploads = [
      upload("a", { kind: "rechazado", reason: "Sin referencias.", byApi: true }),
      upload("b", { kind: "en_espera" }),
      upload("c", { kind: "rechazado", reason: "No es un PDF." }),
    ];
    expect(sendProgress(uploads)).toEqual({ current: 1, total: 2 });
  });
});
