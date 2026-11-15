import { describe, expect, it } from "vitest";
import { cardStyles } from "./card-styles";

describe("cardStyles", () => {
  it("da las mismas clases que se escribían en cada pantalla", () => {
    expect(cardStyles()).toBe("rounded-card border border-hairline bg-canvas");
    expect(cardStyles({ tone: "surface" })).toBe("rounded-card border border-hairline bg-surface");
    expect(cardStyles({ tone: "none" })).toBe("rounded-card border border-hairline");
    expect(cardStyles({ size: "panel" })).toBe("rounded-panel border border-hairline bg-canvas");
    expect(cardStyles({ size: "panel", tone: "surface", strong: true })).toBe(
      "rounded-panel border border-hairline-strong bg-surface",
    );
  });
});
