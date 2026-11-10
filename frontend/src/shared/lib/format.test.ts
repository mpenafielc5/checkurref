import { describe, expect, it } from "vitest";
import { shareLabel, formatDecimal, formatFileSize, formatPercent } from "./format";

describe("formatos de la interfaz", () => {
  it("usa coma decimal, como en las maquetas", () => {
    expect(formatDecimal(0.93)).toBe("0,93");
    expect(formatDecimal(2.4, 1)).toBe("2,4");
  });

  it("redondea los porcentajes", () => {
    expect(formatPercent(70.6)).toBe("71 %");
  });

  it("muestra el tamaño de archivo en MB", () => {
    expect(formatFileSize(2.4 * 1024 * 1024)).toBe("2,4 MB");
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
