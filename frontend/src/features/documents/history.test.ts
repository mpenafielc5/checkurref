import { describe, expect, it } from "vitest";
import { isHistoryDto, toWork, toWorkPage, workHref, type HistoryDto } from "./history";

const ITEM: HistoryDto["items"][number] = {
  analysis_id: "1b6c632b",
  file_name: "Avance_cap2.pdf",
  created_at: "2026-11-03T02:15:31.12345+00:00",
  status: "completado",
  progress: 100,
  total_references: 9,
  index: 88.89,
};

const PAGE: HistoryDto = { items: [ITEM, ITEM], page: 2, page_size: 20, total: 22, total_pages: 2 };

describe("toWork", () => {
  it("traduce un análisis terminado, con la fecha en la hora de Ecuador", () => {
    expect(toWork(ITEM)).toEqual({
      analysisId: "1b6c632b",
      fileName: "Avance_cap2.pdf",
      date: "02/11/2026",
      references: 9,
      index: 89,
      status: "listo",
      progress: 100,
    });
  });

  it("agrupa las etapas en curso y conserva el error", () => {
    for (const status of ["en_cola", "extrayendo", "segmentando", "verificando"]) {
      expect(toWork({ ...ITEM, status }).status).toBe("en_proceso");
    }
    expect(toWork({ ...ITEM, status: "error" }).status).toBe("error");
  });
});

describe("toWorkPage", () => {
  it("calcula el rango mostrado para la paginación", () => {
    const page = toWorkPage(PAGE);

    expect([page.page, page.totalPages, page.total, page.first, page.last]).toEqual([
      2, 2, 22, 21, 22,
    ]);
  });

  it("sin trabajos, el rango es 0", () => {
    const page = toWorkPage({ ...PAGE, items: [], page: 1, total: 0, total_pages: 1 });

    expect([page.first, page.last]).toEqual([0, 0]);
  });
});

describe("workHref", () => {
  it("lleva al informe, al progreso o al motivo del error", () => {
    const done = toWork(ITEM);
    expect(workHref(done)).toBe("/estudiante/trabajos/1b6c632b");
    expect(workHref({ ...done, status: "en_proceso" })).toBe(
      "/estudiante/trabajos/1b6c632b/progreso",
    );
    expect(workHref({ ...done, status: "error" })).toBe("/estudiante/trabajos/1b6c632b");
  });
});

describe("isHistoryDto", () => {
  it("reconoce la respuesta del historial", () => {
    expect(isHistoryDto(PAGE)).toBe(true);
    expect(isHistoryDto({ detail: "Falta el token de sesión." })).toBe(false);
  });
});
