import { describe, expect, it } from "vitest";
import { comparedFieldsOf, toLabComparison } from "./comparison-mapper";

const BODY = {
  engines: [
    {
      engine: "anystyle",
      elapsed_ms: 12,
      error: null,
      fields: { doi: "10.1234/ab", anio: "2021", titulo: null },
    },
    {
      engine: "spacy",
      elapsed_ms: 48,
      error: null,
      fields: { anio: "2020", titulo: null, paginas: "45-60" },
    },
  ],
  different_fields: ["anio"],
  compared_fields: 3,
  matching_fields: 2,
};

describe("toLabComparison", () => {
  it("traduce la salida de cada motor y los campos que no coinciden", () => {
    const comparison = toLabComparison(BODY);

    expect(comparison?.engines[1].elapsedMs).toBe(48);
    expect(comparison?.engines[0].fields?.doi).toBe("10.1234/ab");
    expect(comparison?.differentFields).toEqual(["anio"]);
    expect(comparison?.matchingFields).toBe(2);
  });

  it("acepta un motor que no pudo procesar la referencia", () => {
    const failed = { engine: "anystyle", elapsed_ms: 0, error: "Sin AnyStyle.", fields: null };
    const comparison = toLabComparison({ ...BODY, engines: [failed, BODY.engines[1]] });

    expect(comparison?.engines[0].fields).toBeNull();
    expect(comparison?.engines[0].error).toBe("Sin AnyStyle.");
  });

  it("una respuesta inesperada devuelve null", () => {
    expect(toLabComparison({ ...BODY, engines: [{ engine: "otro" }] })).toBeNull();
    expect(toLabComparison(null)).toBeNull();
  });
});

describe("comparedFieldsOf", () => {
  it("deja los campos que algún motor reconoció, siempre en el mismo orden", () => {
    const comparison = toLabComparison(BODY);
    if (!comparison) throw new Error("Falta la comparación");

    expect(comparedFieldsOf(comparison)).toEqual(["anio", "paginas", "doi"]);
  });
});
