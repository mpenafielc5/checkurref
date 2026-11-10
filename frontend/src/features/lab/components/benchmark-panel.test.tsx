import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchBenchmark, runBenchmark } from "../api";
import type { BenchmarkOverview, BenchmarkRun, EngineId, EngineScores } from "../types";
import { BenchmarkPanel } from "./benchmark-panel";

vi.mock("../api", () => ({
  fetchBenchmark: vi.fn(),
  runBenchmark: vi.fn(),
}));

const fetchMock = vi.mocked(fetchBenchmark);
const runMock = vi.mocked(runBenchmark);

function engine(id: EngineId, keyF1: number, titleF1: number): EngineScores {
  return {
    engine: id,
    version: `${id} 1.0`,
    samples: 100,
    keyF1,
    fields: [
      { field: "titulo", precision: 0.91, recall: 0.9, f1: titleF1 },
      { field: "doi", precision: 1, recall: 1, f1: 1 },
    ],
  };
}

const RUN: BenchmarkRun = {
  executedAt: "2026-11-09T17:30:00Z",
  engines: [engine("anystyle", 0.95, 0.9), engine("spacy", 0.84, 0.6)],
  selectedEngine: "anystyle",
  tie: false,
  difference: 0.11,
};

const OVERVIEW: BenchmarkOverview = {
  goldSet: { total: 150, real: 100, apa: 50, ieee: 50 },
  runs: [RUN],
  engineInUse: "anystyle",
  keyFields: ["titulo", "autores", "anio", "doi"],
  tieMargin: 0.05,
};

async function renderPanel(overview: BenchmarkOverview = OVERVIEW) {
  fetchMock.mockResolvedValue({ kind: "ready", overview });
  render(<BenchmarkPanel />);
  await screen.findByRole("button", { name: "Ejecutar benchmark" });
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("BenchmarkPanel", () => {
  it("muestra el estándar de oro, el motor seleccionado, el motor en uso y la regla", async () => {
    await renderPanel();

    expect(screen.getByText("Estándar de oro: 150 referencias")).toBeTruthy();
    expect(screen.getByText(/Se miden las 100 reales \(50 APA · 50 IEEE\)/)).toBeTruthy();
    expect(screen.getByText("Motor seleccionado")).toBeTruthy();
    expect(screen.getByText("Motor en uso")).toBeTruthy();
    const rule = screen.getByRole("region", { name: "Regla de decisión" });
    expect(rule.textContent).toContain("Título, Autores, Año y DOI");
    expect(rule.textContent).toContain("menor de 5 puntos");
    expect(rule.textContent).toContain("gana AnyStyle con 11,0 puntos");
  });

  it("la tabla trae precisión, exhaustividad y F1 de cada motor por campo", async () => {
    await renderPanel();

    const table = screen.getByRole("table");
    expect(within(table).getByRole("columnheader", { name: "F1 de spaCy" })).toBeTruthy();
    const titleRow = within(table).getByRole("row", { name: /Título/ });
    const cells = within(titleRow)
      .getAllByRole("cell")
      .map((cell) => cell.textContent);
    expect(cells).toEqual(["Título", "0,91", "0,90", "0,90", "0,91", "0,90", "0,60", "AnyStyle"]);
    expect(within(table).getByRole("row", { name: /DOI/ }).textContent).toContain("Empate");
    expect(screen.getByText("Versión de spaCy: spacy 1.0")).toBeTruthy();
  });

  it("el gráfico nombra a cada motor y ubica cada punto según su F1", async () => {
    await renderPanel();

    const figure = screen.getByRole("figure");
    expect(within(figure).getByText("AnyStyle")).toBeTruthy();
    expect(within(figure).getByTitle(/^Título: AnyStyle .* · spaCy 0,60$/)).toBeTruthy();
    // Todos los valores son de 0,5 o más: la escala va de 0,5 a 1 y 0,60 queda al 20 %.
    expect(within(figure).getByTestId("spacy-titulo").style.left).toBe("20%");
  });

  it("el gráfico muestra los dos puntos cuando los motores empatan en un campo", async () => {
    await renderPanel();

    const figure = screen.getByRole("figure");
    expect(within(figure).getByTestId("anystyle-doi").className).toContain("-translate-x-full");
    expect(within(figure).getByTestId("spacy-doi").className).toContain("translate-x-0");
  });

  it("ejecutar guarda la medición y muestra el resultado nuevo", async () => {
    const newest = { ...RUN, executedAt: "2026-11-10T17:30:00Z" };
    runMock.mockResolvedValue({
      kind: "ready",
      overview: { ...OVERVIEW, runs: [newest, RUN] },
    });
    await renderPanel();

    fireEvent.click(screen.getByRole("button", { name: "Ejecutar benchmark" }));

    expect(await screen.findByText("Mediciones anteriores")).toBeTruthy();
    expect(runMock).toHaveBeenCalledTimes(1);
  });

  it("sin AnyStyle muestra el aviso y conserva lo medido", async () => {
    runMock.mockResolvedValue({
      kind: "error",
      message: "AnyStyle no está disponible en el servidor.",
    });
    await renderPanel();

    fireEvent.click(screen.getByRole("button", { name: "Ejecutar benchmark" }));

    expect((await screen.findByRole("alert")).textContent).toContain("AnyStyle no está disponible");
    expect(screen.getByRole("table")).toBeTruthy();
  });

  it("avisa si el motor en uso no es el seleccionado", async () => {
    await renderPanel({ ...OVERVIEW, engineInUse: "spacy" });

    expect(screen.getByRole("status").textContent).toContain(
      "El análisis usa spaCy, pero la última medición seleccionó AnyStyle",
    );
  });

  it("sin mediciones lo dice y aun así muestra la regla y el motor en uso", async () => {
    await renderPanel({ ...OVERVIEW, runs: [] });

    expect(screen.getByText("Aún no hay mediciones")).toBeTruthy();
    expect(screen.getByRole("region", { name: "Regla de decisión" })).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.queryByRole("figure")).toBeNull();
  });

  it("si el panel no carga, muestra el motivo", async () => {
    fetchMock.mockResolvedValue({ kind: "error", message: "No se pudo cargar." });
    render(<BenchmarkPanel />);

    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe("No se pudo cargar."));
  });
});
