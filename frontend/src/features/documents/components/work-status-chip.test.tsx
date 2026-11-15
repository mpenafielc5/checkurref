import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { IndexLevel } from "@/shared/lib/truthfulness";
import type { Work } from "../types";
import { WorkStatusChip } from "./work-status-chip";

function chip(index: number | null, indexLevel: IndexLevel | null): HTMLElement {
  const work: Work = {
    analysisId: "a1",
    fileName: "trabajo.pdf",
    date: "15/11/2026",
    references: 10,
    index,
    indexLevel,
    status: "listo",
    progress: 100,
  };
  render(<WorkStatusChip work={work} />);
  return screen.getByText(/Índice/);
}

describe("WorkStatusChip", () => {
  it("colorea el índice según el nivel que envía el backend", () => {
    expect(chip(100, "alto").className).toContain("verdict-verified");
  });

  it("un índice medio sale en ámbar", () => {
    expect(chip(64.4, "medio").className).toContain("verdict-discrepancy");
  });

  it("un índice bajo sale en rojo, con su decimal", () => {
    const element = chip(33.33, "bajo");

    expect(element.className).toContain("verdict-contradiction");
    expect(element.textContent).toBe("Índice 33,3");
  });

  it("sin nivel no toma color", () => {
    expect(chip(null, null).className).not.toContain("verdict");
  });
});
