import { describe, expect, it } from "vitest";
import { toBatchPage, toBatchSummary, toWorksProgress, type BatchSummaryDto } from "./batch-mapper";

const DTO: BatchSummaryDto = {
  id: "l1",
  name: "Metodología 5B",
  period: "2026-2S",
  total_works: 4,
  finished: 4,
  in_progress: 0,
  failed: 0,
  high_risk: 0,
};

describe("toBatchSummary", () => {
  it("un lote sin trabajos no aparece como revisado", () => {
    expect(toBatchSummary({ ...DTO, total_works: 0, finished: 0 }).status).toEqual({
      kind: "empty",
    });
  });

  it("mientras algo se analiza, cuenta como hechos los terminados y los fallidos", () => {
    const dto = { ...DTO, finished: 1, failed: 1, in_progress: 2 };
    expect(toBatchSummary(dto).status).toEqual({ kind: "analyzing", done: 2 });
  });

  it("si ningún trabajo se pudo analizar, no dice que no hay riesgo", () => {
    expect(toBatchSummary({ ...DTO, finished: 0, failed: 4 }).status).toEqual({ kind: "failed" });
  });

  it("al terminar informa los trabajos de riesgo alto y los que fallaron", () => {
    const summary = toBatchSummary({ ...DTO, finished: 3, failed: 1, high_risk: 2 });
    expect(summary.status).toEqual({ kind: "reviewed", highRisk: 2 });
    expect(summary.failed).toBe(1);
  });
});

describe("toBatchPage", () => {
  it("calcula el rango mostrado de la página", () => {
    const page = toBatchPage({
      items: [DTO, { ...DTO, id: "l2" }],
      page: 2,
      page_size: 20,
      total: 22,
      total_pages: 2,
    });
    expect(page).toMatchObject({ first: 21, last: 22, total: 22, totalPages: 2 });
  });

  it("sin lotes el rango queda en cero", () => {
    const page = toBatchPage({ items: [], page: 1, page_size: 20, total: 0, total_pages: 1 });
    expect(page).toMatchObject({ first: 0, last: 0 });
  });
});

describe("toWorksProgress", () => {
  it("traduce el avance de cada trabajo", () => {
    const works = [
      {
        analysis_id: "a1",
        status: "verificando",
        progress: 40,
        total_references: 22,
        error_message: null,
      },
    ];
    expect(toWorksProgress({ works })).toEqual([
      {
        analysisId: "a1",
        status: "verificando",
        progress: 40,
        totalReferences: 22,
        errorMessage: null,
      },
    ]);
  });

  it("una respuesta inesperada no se toma como un lote vacío", () => {
    expect(toWorksProgress({ detail: "No se encontró el lote." })).toBeNull();
    expect(toWorksProgress(null)).toBeNull();
  });
});
