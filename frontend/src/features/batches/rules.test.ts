import { describe, expect, it } from "vitest";
import { authorsLabel, shareLabel, sortBatchWorks } from "./rules";
import type { BatchWork } from "./types";

const work = (
  name: string,
  risk: BatchWork["risk"],
  index: number | null,
  alerts: number,
): BatchWork => ({
  analysisId: name,
  fileName: "Avance 2.pdf",
  authors: [name],
  status: "completado",
  progress: 100,
  references: 10,
  index,
  alerts,
  risk,
  errorMessage: null,
});

const inProgress = (name: string): BatchWork => ({
  ...work(name, null, null, 0),
  status: "verificando",
  progress: 50,
});

const WORKS = [
  work("Bajo", "bajo", 95, 0),
  work("Alto", "alto", 58, 6),
  work("Medio con índice bajo", "medio", 71, 3),
  work("Medio con índice alto", "medio", 77, 2),
];

describe("authorsLabel", () => {
  it("muestra los autores de la portada separados por comas", () => {
    expect(authorsLabel({ ...WORKS[0], authors: ["Ana Torres", "Luis Vera"] })).toBe(
      "Ana Torres, Luis Vera",
    );
  });

  it("sin autores reconocidos devuelve null", () => {
    expect(authorsLabel({ ...WORKS[0], authors: [] })).toBeNull();
  });
});

describe("sortBatchWorks", () => {
  it("pone primero los trabajos de mayor riesgo y, a igual riesgo, el de menor índice", () => {
    expect(sortBatchWorks(WORKS).map(authorsLabel)).toEqual([
      "Alto",
      "Medio con índice bajo",
      "Medio con índice alto",
      "Bajo",
    ]);
  });

  it("ordena por cualquier columna en ambos sentidos", () => {
    expect(sortBatchWorks(WORKS, "alerts", "asc").map((w) => w.alerts)).toEqual([0, 2, 3, 6]);
    expect(sortBatchWorks(WORKS, "index", "desc")[0].index).toBe(95);
  });

  it("por nombre, deja al final los trabajos con portada no reconocida", () => {
    const unknown = { ...WORKS[0], authors: [], fileName: "avance2.pdf" };
    const names = sortBatchWorks([unknown, ...WORKS], "name", "asc").map(
      (w) => authorsLabel(w) ?? w.fileName,
    );
    expect(names).toEqual([
      "Alto",
      "Bajo",
      "Medio con índice alto",
      "Medio con índice bajo",
      "avance2.pdf",
    ]);
  });

  it("los trabajos sin resultado quedan al final en ambos sentidos", () => {
    const works = [inProgress("Analizando"), ...WORKS];

    for (const direction of ["asc", "desc"] as const) {
      expect(sortBatchWorks(works, "risk", direction).at(-1)?.authors).toEqual(["Analizando"]);
      expect(sortBatchWorks(works, "index", direction).at(-1)?.authors).toEqual(["Analizando"]);
    }
  });

  it("un trabajo terminado sin riesgo calculado no se adelanta a los que lo tienen", () => {
    const works = [work("Sin índice", null, null, 0), ...WORKS];

    expect(sortBatchWorks(works).at(-1)?.authors).toEqual(["Sin índice"]);
  });

  it("no modifica la lista original", () => {
    const copy = [...WORKS];
    sortBatchWorks(WORKS, "name");
    expect(WORKS).toEqual(copy);
  });
});

describe("shareLabel", () => {
  it("redondea el porcentaje de las referencias", () => {
    expect(shareLabel(71, 100)).toBe("71 %");
    expect(shareLabel(0, 100)).toBe("0 %");
    expect(shareLabel(100, 100)).toBe("100 %");
  });

  it("no redondea a 0 % ni a 100 % lo que no es exacto", () => {
    expect(shareLabel(1, 300)).toBe("< 1 %");
    expect(shareLabel(299, 300)).toBe("> 99 %");
  });

  it("sin referencias no hay porcentaje", () => {
    expect(shareLabel(0, 0)).toBe("—");
  });
});
