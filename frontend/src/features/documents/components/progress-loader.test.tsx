import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ProgressState } from "../use-analysis-progress";
import { ProgressLoader } from "./progress-loader";

let state: ProgressState = { kind: "loading", slow: false };

vi.mock("../use-analysis-progress", () => ({ useAnalysisProgress: () => state }));
vi.mock("next/navigation", () => ({
  useParams: () => ({ analisisId: "a1" }),
  useRouter: () => ({ replace: vi.fn() }),
}));

describe("ProgressLoader", () => {
  it("un análisis fallido explica el motivo y lleva a subir el PDF corregido", () => {
    state = {
      kind: "ready",
      analysis: {
        status: "error",
        progress: 0,
        totalReferences: null,
        norm: null,
        errorMessage: "No se encontró la sección de referencias.",
        fileName: "tarea.pdf",
        createdAt: "2026-11-08T10:00:00Z",
      },
    };
    render(<ProgressLoader />);

    expect(screen.getByRole("alert").textContent).toContain(
      "No se encontró la sección de referencias.",
    );
    expect(screen.getByRole("link", { name: "Subir el PDF corregido" }).getAttribute("href")).toBe(
      "/estudiante",
    );
    expect(screen.getByRole("link", { name: "Volver a mis trabajos" }).getAttribute("href")).toBe(
      "/estudiante/trabajos",
    );
  });

  it("si no se puede abrir el análisis lo dice en un recuadro con el regreso", () => {
    state = { kind: "error", message: "No se encontró este análisis." };
    render(<ProgressLoader />);

    expect(screen.getByRole("alert").textContent).toContain("No se encontró este análisis.");
    expect(screen.getByRole("link", { name: "Volver a mis trabajos" })).toBeTruthy();
  });
});
