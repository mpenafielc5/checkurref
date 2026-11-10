import { describe, expect, it } from "vitest";
import { analysisHref } from "./upload-rules";

describe("analysisHref", () => {
  it("lleva al informe si terminó y al progreso si sigue", () => {
    expect(analysisHref("a1", true)).toBe("/estudiante/trabajos/a1");
    expect(analysisHref("a1", false)).toBe("/estudiante/trabajos/a1/progreso");
  });
});
