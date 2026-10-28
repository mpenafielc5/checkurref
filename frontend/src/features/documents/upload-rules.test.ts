import { describe, expect, it } from "vitest";
import { analysisHref, interpretUploadResponse, withTimeout } from "./upload-rules";

const SUBMITTED = { analysis_id: "a1", document_id: "d1", status: "en_cola", duplicate: false };

describe("interpretUploadResponse", () => {
  it("un análisis nuevo lleva a su progreso", () => {
    expect(interpretUploadResponse(202, SUBMITTED)).toEqual({ kind: "created", analysisId: "a1" });
  });

  it("un PDF repetido ofrece el análisis existente y dice si ya terminó", () => {
    expect(
      interpretUploadResponse(200, { ...SUBMITTED, status: "completado", duplicate: true }),
    ).toEqual({ kind: "duplicate", analysisId: "a1", finished: true });
    expect(interpretUploadResponse(200, { ...SUBMITTED, duplicate: true })).toMatchObject({
      finished: false,
    });
  });

  it("muestra el motivo que da la API", () => {
    expect(interpretUploadResponse(422, { detail: "Solo se aceptan archivos PDF." })).toEqual({
      kind: "error",
      message: "Solo se aceptan archivos PDF.",
    });
  });

  it("sin sesión pide volver a ingresar", () => {
    expect(interpretUploadResponse(401, null)).toMatchObject({
      message: expect.stringContaining("sesión venció"),
    });
  });

  it("ante errores sin texto propio usa un mensaje general", () => {
    expect(interpretUploadResponse(422, { detail: [{ loc: ["body", "norma"] }] })).toMatchObject({
      message: expect.stringContaining("No se pudo subir"),
    });
    expect(interpretUploadResponse(500, null)).toMatchObject({ kind: "error" });
  });
});

describe("withTimeout", () => {
  it("devuelve el valor si llega a tiempo", async () => {
    await expect(withTimeout(Promise.resolve("token"), 50)).resolves.toBe("token");
  });

  it("devuelve null si la promesa no responde", async () => {
    const never = new Promise<string>(() => undefined);
    await expect(withTimeout(never, 10)).resolves.toBeNull();
  });

  it("deja pasar el error de la promesa", async () => {
    await expect(withTimeout(Promise.reject(new Error("caída")), 50)).rejects.toThrow("caída");
  });
});

describe("analysisHref", () => {
  it("lleva al informe si terminó y al progreso si sigue", () => {
    expect(analysisHref("a1", true)).toBe("/estudiante/trabajos/a1");
    expect(analysisHref("a1", false)).toBe("/estudiante/trabajos/a1/progreso");
  });
});
