import { describe, expect, it } from "vitest";
import { toBenchmarkOverview } from "./benchmark-mapper";

const RUN = {
  executed_at: "2026-11-09T17:30:00Z",
  engines: [
    {
      engine: "anystyle",
      version: "anystyle 1.6.0",
      samples: 100,
      key_f1: 0.95,
      fields: [{ field: "titulo", precision: 0.91, recall: 0.9, f1: 0.9 }],
    },
  ],
  selected_engine: "anystyle",
  tie: false,
  difference: 0.11,
};

const BODY = {
  gold_set: { total: 150, real: 100, apa: 50, ieee: 50 },
  runs: [RUN],
  engine_in_use: "anystyle",
  key_fields: ["titulo", "autores", "anio", "doi"],
  tie_margin: 0.05,
};

describe("toBenchmarkOverview", () => {
  it("traduce el estándar de oro, las mediciones y el motor en uso", () => {
    const overview = toBenchmarkOverview(BODY);

    expect(overview?.goldSet.real).toBe(100);
    expect(overview?.engineInUse).toBe("anystyle");
    expect(overview?.tieMargin).toBe(0.05);
    expect(overview?.runs[0].selectedEngine).toBe("anystyle");
    expect(overview?.runs[0].engines[0].keyF1).toBe(0.95);
    expect(overview?.runs[0].engines[0].fields[0].precision).toBe(0.91);
  });

  it("sin mediciones la lista queda vacía", () => {
    expect(toBenchmarkOverview({ ...BODY, runs: [] })?.runs).toEqual([]);
  });

  it("una respuesta inesperada devuelve null", () => {
    expect(toBenchmarkOverview({ ...BODY, engine_in_use: "otro" })).toBeNull();
    expect(toBenchmarkOverview({ ...BODY, runs: [{ ...RUN, tie: "no" }] })).toBeNull();
    expect(toBenchmarkOverview(null)).toBeNull();
  });
});
