import { describe, expect, it } from "vitest";
import { MAX_PDF_BYTES, validatePdfFile } from "./pdf-rules";

describe("validatePdfFile", () => {
  it("acepta un PDF de hasta 10 MB", () => {
    expect(
      validatePdfFile({ name: "avance.pdf", type: "application/pdf", size: 2_000_000 }),
    ).toEqual({ ok: true });
    expect(
      validatePdfFile({ name: "limite.pdf", type: "application/pdf", size: MAX_PDF_BYTES }),
    ).toEqual({ ok: true });
  });

  it("acepta un PDF aunque el navegador no informe el tipo", () => {
    expect(validatePdfFile({ name: "AVANCE.PDF", type: "", size: 1000 })).toEqual({ ok: true });
  });

  it("rechaza otros formatos, archivos grandes y archivos vacíos", () => {
    expect(
      validatePdfFile({ name: "avance.docx", type: "application/msword", size: 1000 }).ok,
    ).toBe(false);
    expect(
      validatePdfFile({ name: "grande.pdf", type: "application/pdf", size: MAX_PDF_BYTES + 1 }).ok,
    ).toBe(false);
    expect(validatePdfFile({ name: "vacio.pdf", type: "application/pdf", size: 0 }).ok).toBe(false);
  });
});
