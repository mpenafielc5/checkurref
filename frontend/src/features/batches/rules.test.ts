import { describe, expect, it } from "vitest";
import { authorsLabel, sortBatchWorks } from "./rules";
import type { BatchWork } from "./types";

const work = (name: string, risk: BatchWork["risk"], index: number, alerts: number): BatchWork => ({
  analysisId: name,
  fileName: "Avance 2.pdf",
  authors: [name],
  references: 10,
  index,
  alerts,
  risk,
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

  it("no modifica la lista original", () => {
    const copy = [...WORKS];
    sortBatchWorks(WORKS, "name");
    expect(WORKS).toEqual(copy);
  });
});
