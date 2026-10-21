import { describe, expect, it } from "vitest";
import { formatDecimal, formatFileSize, formatPercent } from "./format";

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
