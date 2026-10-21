import { describe, expect, it } from "vitest";
import { sortBatchWorks } from "./rules";
import type { BatchWork } from "./types";

const work = (name: string, risk: BatchWork["risk"], index: number, alerts: number): BatchWork => ({
  analysisId: name,
  name,
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

describe("sortBatchWorks", () => {
  it("pone primero los trabajos de mayor riesgo y, a igual riesgo, el de menor índice", () => {
    expect(sortBatchWorks(WORKS).map((w) => w.name)).toEqual([
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

  it("no modifica la lista original", () => {
    const copy = [...WORKS];
    sortBatchWorks(WORKS, "name");
    expect(WORKS).toEqual(copy);
  });
});
