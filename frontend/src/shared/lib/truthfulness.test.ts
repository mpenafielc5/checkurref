import { describe, expect, it } from "vitest";
import { indexExplanation, toIndexLevel } from "./truthfulness";

const COUNTS = {
  verificada: 17,
  discrepancia: 2,
  contradiccion: 0,
  sin_respaldo: 1,
  no_verificable: 3,
};

describe("toIndexLevel", () => {
  it("acepta solo los niveles que calcula el backend", () => {
    expect(toIndexLevel("alto")).toBe("alto");
    expect(toIndexLevel("medio")).toBe("medio");
    expect(toIndexLevel("bajo")).toBe("bajo");
    expect(toIndexLevel(null)).toBeNull();
    expect(toIndexLevel(undefined)).toBeNull();
    expect(toIndexLevel("otro")).toBeNull();
  });
});

describe("indexExplanation", () => {
  it("cuenta todas menos las no verificables", () => {
    expect(indexExplanation(COUNTS)).toBe("17 de 20 referencias comprobadas están verificadas.");
  });

  it("concuerda en número con una sola referencia", () => {
    expect(indexExplanation({ ...COUNTS, verificada: 1, discrepancia: 0, sin_respaldo: 0 })).toBe(
      "1 de 1 referencia comprobada está verificada.",
    );
  });
});
