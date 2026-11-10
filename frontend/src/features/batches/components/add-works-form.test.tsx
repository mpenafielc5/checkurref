import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createBatch, fetchBatchProgress, submitBatchWork } from "../api";
import type { BatchDetail } from "../types";
import { AddWorksForm } from "./add-works-form";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useParams: () => ({ loteId: "lote-1" }),
  useRouter: () => ({ push }),
}));

vi.mock("../api", () => ({
  createBatch: vi.fn(),
  fetchBatchDetail: vi.fn(),
  fetchBatchProgress: vi.fn(),
  submitBatchWork: vi.fn(),
  wakeApi: vi.fn(),
}));

const submitMock = vi.mocked(submitBatchWork);

function batchWith(totalWorks: number): BatchDetail {
  return {
    id: "lote-1",
    name: "Metodología 5B",
    period: "2026-2S",
    totalWorks,
    finished: totalWorks,
    inProgress: 0,
    failed: 0,
    references: 0,
    counts: {
      verificada: 0,
      discrepancia: 0,
      contradiccion: 0,
      sin_respaldo: 0,
      no_verificable: 0,
    },
    queryErrors: 0,
    mostDifferentFields: [],
    works: [],
  };
}

function pdf(name: string): File {
  return new File(["%PDF-1.7"], name, { type: "application/pdf" });
}

function choose(files: File[]) {
  const input = document.querySelector<HTMLInputElement>('input[type="file"]');
  if (!input) throw new Error("Falta el campo de archivo");
  fireEvent.change(input, { target: { files } });
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(fetchBatchProgress).mockResolvedValue([]);
});

describe("AddWorksForm", () => {
  it("sube los archivos al mismo lote, sin crear otro", async () => {
    submitMock.mockResolvedValue({ kind: "created", analysisId: "a9" });
    render(<AddWorksForm batch={batchWith(2)} />);

    expect(screen.getByText(/Hasta 38 PDF más en este lote/)).toBeTruthy();
    choose([pdf("Olvidado.pdf")]);
    fireEvent.click(screen.getByRole("button", { name: "Agregar al lote (1 archivo)" }));

    await waitFor(() => expect(submitMock).toHaveBeenCalledTimes(1));
    expect(submitMock.mock.calls[0]?.[0]).toBe("lote-1");
    expect(createBatch).not.toHaveBeenCalled();
    expect(await screen.findByText("Olvidado.pdf")).toBeTruthy();
    // Todo se envió bien: el avance sigue en el tablero.
    await waitFor(() => expect(push).toHaveBeenCalledWith("/docente/lotes/lote-1"));
  });

  it("si un archivo falla, se queda para mostrar el motivo", async () => {
    submitMock.mockResolvedValue({ kind: "error", message: "No se pudo subir el archivo." });
    render(<AddWorksForm batch={batchWith(2)} />);

    choose([pdf("Olvidado.pdf")]);
    fireEvent.click(screen.getByRole("button", { name: "Agregar al lote (1 archivo)" }));

    expect(await screen.findByText(/No se pudo subir el archivo/)).toBeTruthy();
    expect(push).not.toHaveBeenCalled();
  });

  it("no acepta más archivos de los que caben en el lote", () => {
    render(<AddWorksForm batch={batchWith(39)} />);

    choose([pdf("Uno.pdf"), pdf("Dos.pdf")]);

    expect(screen.getByRole("button", { name: "Agregar al lote (1 archivo)" })).toBeTruthy();
    expect(screen.getByText(/admite 1 archivo más; se conservó el primero/)).toBeTruthy();
  });

  it("con el lote lleno lo explica en lugar de mostrar la subida", () => {
    render(<AddWorksForm batch={batchWith(40)} />);

    expect(screen.getByText(/El lote está completo: tiene 40 trabajos/)).toBeTruthy();
    expect(document.querySelector('input[type="file"]')).toBeNull();
  });
});
