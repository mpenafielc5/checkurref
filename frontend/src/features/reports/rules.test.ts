import { describe, expect, it } from "vitest";
import { filterByVerdict, parseVerdictFilter, referenceText, startsCollapsed } from "./rules";
import { SAMPLE_REPORT } from "./sample-data";

const REFERENCES = SAMPLE_REPORT.references;

describe("parseVerdictFilter", () => {
  it("acepta los cinco veredictos", () => {
    expect(parseVerdictFilter("contradiccion")).toBe("contradiccion");
  });

  it("sin valor o con uno desconocido no filtra", () => {
    for (const raw of [null, undefined, "", "falsa", "Contradiccion"]) {
      expect(parseVerdictFilter(raw)).toBeNull();
    }
  });
});

describe("filterByVerdict", () => {
  it("deja solo las referencias del veredicto, en su orden", () => {
    const orders = filterByVerdict(REFERENCES, "discrepancia").map((r) => r.order);
    expect(orders).toEqual([3, 7, 15, 22, 29]);
  });

  it("cada filtro coincide con el conteo del resumen", () => {
    for (const [verdict, count] of Object.entries(SAMPLE_REPORT.counts)) {
      expect(filterByVerdict(REFERENCES, parseVerdictFilter(verdict))).toHaveLength(count);
    }
  });

  it("sin filtro devuelve todas", () => {
    expect(filterByVerdict(REFERENCES, null)).toHaveLength(34);
  });
});

describe("startsCollapsed", () => {
  const verified = REFERENCES.find(
    (r) => r.verdict === "verificada" && r.formatFindings.length === 0,
  );

  it("cierra las verificadas sin nada que corregir", () => {
    expect(verified && startsCollapsed(verified)).toBe(true);
  });

  it("deja abiertas las verificadas con hallazgos de formato", () => {
    expect(
      verified &&
        startsCollapsed({
          ...verified,
          formatFindings: [{ message: "Falta el DOI.", given: "", expected: "" }],
        }),
    ).toBe(false);
  });

  it("deja abiertas las que tienen cualquier otro veredicto", () => {
    for (const reference of REFERENCES.filter((r) => r.verdict !== "verificada")) {
      expect(startsCollapsed(reference)).toBe(false);
    }
  });
});

describe("referenceText", () => {
  it("une los fragmentos coloreados en una sola línea de texto", () => {
    expect(referenceText(REFERENCES[0])).toMatch(/^Torres, A\. y Vera, C\. \(2019\)\. /);
  });
});
