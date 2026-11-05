import { describe, expect, it } from "vitest";
import {
  isAnalysisItemDto,
  mergeSnapshot,
  snapshotFromRow,
  toAnalysisInfo,
  toSteps,
  verifiedCount,
  verifyPercent,
  type AnalysisInfo,
  type AnalysisSnapshot,
} from "./progress";

const DTO = {
  analysis_id: "1b6c632b",
  document_id: "7d1e",
  file_name: "Avance_cap2.pdf",
  created_at: "2026-11-03T02:15:31.12345+00:00",
  status: "verificando",
  progress: 56,
  total_references: 10,
  norm: "APA",
  index: null,
  error_message: null,
};

const INFO: AnalysisInfo = toAnalysisInfo(DTO);

function snapshot(status: string, progress: number, total: number | null = 10): AnalysisSnapshot {
  return { status, progress, totalReferences: total, norm: "APA", errorMessage: null };
}

describe("isAnalysisItemDto y toAnalysisInfo", () => {
  it("reconoce el estado de la API y lo traduce", () => {
    expect(isAnalysisItemDto(DTO)).toBe(true);
    expect(isAnalysisItemDto({ detail: "No encontrado" })).toBe(false);
    expect(isAnalysisItemDto(null)).toBe(false);
    expect(INFO).toEqual({
      fileName: "Avance_cap2.pdf",
      createdAt: "2026-11-03T02:15:31.12345+00:00",
      status: "verificando",
      progress: 56,
      totalReferences: 10,
      norm: "APA",
      errorMessage: null,
    });
  });
});

describe("snapshotFromRow", () => {
  it("lee la fila de analisis que llega por Realtime", () => {
    const row = {
      id: "1b6c632b",
      estado: "error",
      progreso: 20,
      total_referencias: 12,
      norma_detectada: "IEEE",
      mensaje_error: "No se encontró la sección de referencias.",
    };
    expect(snapshotFromRow(row)).toEqual({
      status: "error",
      progress: 20,
      totalReferences: 12,
      norm: "IEEE",
      errorMessage: "No se encontró la sección de referencias.",
    });
  });

  it("deja en null lo que aún no existe y descarta filas incompletas", () => {
    expect(snapshotFromRow({ estado: "en_cola", progreso: 0 })).toEqual({
      ...snapshot("en_cola", 0, null),
      norm: null,
    });
    expect(snapshotFromRow({ estado: "en_cola" })).toBeNull();
    expect(snapshotFromRow("analisis")).toBeNull();
  });
});

describe("mergeSnapshot", () => {
  it("avanza con un estado posterior o con más avance", () => {
    expect(mergeSnapshot(INFO, snapshot("verificando", 60)).progress).toBe(60);
    expect(mergeSnapshot(INFO, snapshot("completado", 100)).status).toBe("completado");
    expect(mergeSnapshot(INFO, snapshot("error", 56)).status).toBe("error");
  });

  it("ignora un estado que llega tarde y haría retroceder la pantalla", () => {
    expect(mergeSnapshot(INFO, snapshot("verificando", 40))).toBe(INFO);
    expect(mergeSnapshot(INFO, snapshot("segmentando", 20))).toBe(INFO);
  });

  it("conserva el nombre y la fecha del archivo", () => {
    const merged = mergeSnapshot(INFO, snapshot("verificando", 95));
    expect(merged.fileName).toBe("Avance_cap2.pdf");
    expect(merged.createdAt).toBe(INFO.createdAt);
  });
});

describe("verifiedCount y verifyPercent", () => {
  it("deduce las referencias verificadas del avance que informa el backend", () => {
    // Backend: 30 + 65 * verificadas // total.
    for (const total of [1, 9, 34, 65]) {
      for (let done = 0; done <= total; done += 1) {
        const progress = 30 + Math.floor((65 * done) / total);
        expect(verifiedCount(progress, total)).toBe(done);
      }
    }
  });

  it("con más de 65 referencias nunca se adelanta a lo real", () => {
    const total = 120;
    for (let done = 0; done <= total; done += 1) {
      const progress = 30 + Math.floor((65 * done) / total);
      expect(verifiedCount(progress, total)).toBeLessThanOrEqual(done);
    }
  });

  it("se queda en los límites antes y después de verificar", () => {
    expect(verifiedCount(20, 10)).toBe(0);
    expect(verifiedCount(100, 10)).toBe(10);
    expect(verifiedCount(50, null)).toBe(0);
    expect(verifyPercent(20)).toBe(0);
    expect(verifyPercent(62.5)).toBe(50);
    expect(verifyPercent(100)).toBe(100);
  });
});

describe("toSteps", () => {
  const states = (value: AnalysisSnapshot) => toSteps(value).map((step) => step.state);

  it("en cola: el archivo está subido y la extracción espera", () => {
    const steps = toSteps(snapshot("en_cola", 0, null));
    expect(states(snapshot("en_cola", 0, null))).toEqual([
      "done",
      "current",
      "pending",
      "pending",
      "pending",
    ]);
    expect(steps[1]?.detail).toBe("En cola; el análisis comenzará en breve");
    expect(steps[2]?.title).toBe("Referencias detectadas");
    expect(steps[3]?.detail).toBe("Pendiente");
  });

  it("separando: ya muestra cuántas referencias detectó", () => {
    const steps = toSteps(snapshot("segmentando", 20, 34));
    expect(states(snapshot("segmentando", 20, 34))).toEqual([
      "done",
      "done",
      "current",
      "pending",
      "pending",
    ]);
    expect(steps[2]?.title).toBe("34 referencias detectadas");
    expect(toSteps(snapshot("segmentando", 20, 1))[2]?.title).toBe("1 referencia detectada");
  });

  it("verificando: cuenta las referencias verificadas", () => {
    const steps = toSteps(snapshot("verificando", 56, 10));
    expect(steps[3]).toEqual({
      title: "Verificando con Crossref, OpenAlex y NLI",
      detail: "4 de 10 referencias",
      state: "current",
    });
  });

  it("completado: todas las etapas terminadas", () => {
    const steps = toSteps(snapshot("completado", 100, 1));
    expect(steps.every((step) => step.state === "done")).toBe(true);
    expect(steps[3]?.detail).toBe("1 referencia verificada");
    expect(steps[4]?.detail).toBe("Abriendo el informe…");
  });
});
