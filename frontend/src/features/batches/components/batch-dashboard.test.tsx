import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchBatchDetail } from "../api";
import type { BatchDetail, BatchWork } from "../types";
import { POLL_MS } from "../use-batch-upload";
import { BatchDashboard, BatchDashboardView } from "./batch-dashboard";

const route = vi.hoisted(() => ({
  search: "",
  replace: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ loteId: "lote-1" }),
  usePathname: () => "/docente/lotes/lote-1",
  useRouter: () => ({ replace: route.replace }),
  useSearchParams: () => new URLSearchParams(route.search),
}));

vi.mock("../api", () => ({
  fetchBatchDetail: vi.fn(),
  createBatch: vi.fn(),
  fetchBatchProgress: vi.fn(),
  submitBatchWork: vi.fn(),
  wakeApi: vi.fn(),
}));

const fetchMock = vi.mocked(fetchBatchDetail);

function work(id: string, overrides: Partial<BatchWork> = {}): BatchWork {
  return {
    analysisId: id,
    fileName: `${id}.pdf`,
    authors: [`Autor ${id}`],
    status: "completado",
    progress: 100,
    references: 10,
    index: 90,
    alerts: 0,
    risk: "bajo",
    errorMessage: null,
    ...overrides,
  };
}

const BATCH: BatchDetail = {
  id: "lote-1",
  name: "Metodología 5B",
  period: "2026-2S",
  totalWorks: 2,
  finished: 2,
  inProgress: 0,
  failed: 0,
  references: 20,
  counts: { verificada: 15, discrepancia: 3, contradiccion: 1, sin_respaldo: 1, no_verificable: 0 },
  queryErrors: 0,
  mostDifferentFields: [{ field: "anio", references: 3 }],
  works: [work("bajo"), work("alto", { risk: "alto", index: 50, alerts: 4 })],
};

function tableOrder(): string[] {
  const table = screen.getByRole("table");
  return within(table)
    .getAllByRole("row")
    .slice(1)
    .map((row) => within(row).getAllByRole("cell")[0].textContent ?? "");
}

beforeEach(() => {
  vi.clearAllMocks();
  route.search = "";
});

afterEach(() => {
  vi.useRealTimers();
});

describe("BatchDashboardView", () => {
  it("muestra los indicadores, el porcentaje por veredicto y los campos con diferencias", () => {
    render(<BatchDashboardView batch={BATCH} />);

    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Metodología 5B");
    const verdicts = screen.getByRole("region", { name: "Veredictos del lote" });
    expect(verdicts.textContent).toContain("75 % (15)");
    const fields = screen.getByRole("region", { name: "Campos con más diferencias" });
    expect(fields.textContent).toContain("Año");
    expect(fields.textContent).toContain("3 referencias");
  });

  it("ordena por riesgo de mayor a menor y cada encabezado cambia el orden", () => {
    render(<BatchDashboardView batch={BATCH} />);

    expect(tableOrder()[0]).toContain("Autor alto");

    fireEvent.click(screen.getByRole("button", { name: "Riesgo" }));
    expect(tableOrder()[0]).toContain("Autor bajo");

    fireEvent.click(screen.getByRole("button", { name: "Alertas" }));
    expect(tableOrder()[0]).toContain("Autor alto");
  });

  it("el trabajo terminado abre su informe; el que no terminó no es un enlace", () => {
    const batch = {
      ...BATCH,
      works: [
        work("listo"),
        work("cola", { status: "en_cola", risk: null, index: null, references: null }),
      ],
    };
    render(<BatchDashboardView batch={batch} />);

    const table = within(screen.getByRole("table"));
    expect(table.getByRole("link", { name: /Autor listo/ }).getAttribute("href")).toBe(
      "/docente/lotes/lote-1/listo",
    );
    expect(table.queryByRole("link", { name: /Autor cola/ })).toBeNull();
    expect(table.getByText("En cola")).toBeTruthy();
  });

  it("identifica por el archivo si la portada no se reconoció y muestra el motivo del error", () => {
    const batch = {
      ...BATCH,
      failed: 1,
      works: [
        work("sin-portada", {
          authors: [],
          status: "error",
          risk: null,
          errorMessage: "PDF dañado.",
        }),
      ],
    };
    render(<BatchDashboardView batch={batch} />);

    const row = tableOrder()[0];
    expect(row).toContain("Portada no reconocida");
    expect(row).toContain("sin-portada.pdf");
    expect(row).toContain("PDF dañado.");
    expect(screen.getByText(/1 trabajo no se pudo analizar/)).toBeTruthy();
  });

  it("pagina de 20 en 20 y un orden nuevo vuelve a la primera página", () => {
    route.search = "pagina=2";
    const works = Array.from({ length: 25 }, (_, position) => work(`t${position}`));
    render(<BatchDashboardView batch={{ ...BATCH, totalWorks: 25, works }} />);

    expect(tableOrder()).toHaveLength(5);
    expect(screen.getByText("Mostrando 21–25 de 25 trabajos")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Índice" }));

    expect(route.replace).toHaveBeenCalledWith("/docente/lotes/lote-1", { scroll: false });
  });

  it("un lote sin trabajos lo dice en lugar de mostrar indicadores en cero", () => {
    render(<BatchDashboardView batch={{ ...BATCH, totalWorks: 0, references: 0, works: [] }} />);

    expect(screen.getByText("Este lote aún no tiene trabajos.")).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
  });
});

describe("BatchDashboard", () => {
  it("si el lote no existe, muestra el motivo", async () => {
    fetchMock.mockResolvedValue({ kind: "error", message: "No se encontró este lote." });
    render(<BatchDashboard />);

    expect((await screen.findByRole("alert")).textContent).toBe("No se encontró este lote.");
    expect(fetchMock).toHaveBeenCalledWith("lote-1", expect.any(Function));
  });

  it("consulta de nuevo solo mientras hay análisis en curso y conserva lo visible si falla", async () => {
    vi.useFakeTimers();
    const running = {
      ...BATCH,
      finished: 1,
      inProgress: 1,
      works: [work("uno"), work("dos", { status: "verificando", risk: null, index: null })],
    };
    fetchMock
      .mockResolvedValueOnce({ kind: "ready", batch: running })
      .mockResolvedValueOnce({ kind: "error", message: "Sin conexión." })
      .mockResolvedValueOnce({ kind: "ready", batch: BATCH });
    render(<BatchDashboard />);

    await act(async () => vi.advanceTimersByTimeAsync(0));
    expect(screen.getByText(/1 de 2 trabajos terminados/)).toBeTruthy();

    await act(async () => vi.advanceTimersByTimeAsync(POLL_MS));
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.getByText(/1 de 2 trabajos terminados/)).toBeTruthy();

    await act(async () => vi.advanceTimersByTimeAsync(POLL_MS));
    expect(screen.queryByText(/trabajos terminados/)).toBeNull();

    await act(async () => vi.advanceTimersByTimeAsync(POLL_MS * 3));
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});
