import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Activity } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createBatch, fetchBatchProgress, submitBatchWork } from "../api";
import { POLL_MS } from "../use-batch-upload";
import { NewBatchForm } from "./new-batch-form";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("../api", () => ({
  createBatch: vi.fn(),
  fetchBatchProgress: vi.fn(),
  submitBatchWork: vi.fn(),
  wakeApi: vi.fn(),
}));

const createMock = vi.mocked(createBatch);
const submitMock = vi.mocked(submitBatchWork);
const progressMock = vi.mocked(fetchBatchProgress);

const BATCH = { id: "lote-1", name: "Metodología 5B", period: "2026-2S" };

function pdf(name: string): File {
  return new File(["%PDF-1.7"], name, { type: "application/pdf" });
}

function fillForm(files: File[], name = "Metodología 5B", period = "2026-2S") {
  fireEvent.change(screen.getByLabelText("Nombre del lote"), { target: { value: name } });
  fireEvent.change(screen.getByLabelText("Periodo"), { target: { value: period } });
  const input = document.querySelector<HTMLInputElement>('input[type="file"]');
  if (!input) throw new Error("Falta el campo de archivo");
  fireEvent.change(input, { target: { files } });
}

function submit() {
  fireEvent.click(screen.getByRole("button", { name: /Analizar lote/ }));
}

function rowOf(fileName: string): HTMLElement {
  const row = screen.getByText(fileName).closest("li");
  if (!row) throw new Error(`Falta la fila de ${fileName}`);
  return row;
}

beforeEach(() => {
  vi.clearAllMocks();
  createMock.mockResolvedValue({ kind: "created", batch: BATCH });
  progressMock.mockResolvedValue([]);
});

afterEach(() => {
  vi.useRealTimers();
});

function page(mode: "visible" | "hidden") {
  return (
    <Activity mode={mode}>
      <NewBatchForm />
    </Activity>
  );
}

describe("NewBatchForm", () => {
  it("al volver a la página después de enviar el lote, empieza uno nuevo", async () => {
    submitMock.mockResolvedValue({ kind: "created", analysisId: "a1" });
    const { rerender } = render(page("visible"));
    fillForm([pdf("Ensayo.pdf")]);
    submit();
    expect(await screen.findByText("Ensayo.pdf")).toBeTruthy();
    await waitFor(() => expect(submitMock).toHaveBeenCalledTimes(1));

    // Next.js oculta la página con Activity al navegar y la vuelve a mostrar al regresar.
    await act(async () => rerender(page("hidden")));
    await act(async () => rerender(page("visible")));

    const nameInput = screen.getByLabelText<HTMLInputElement>("Nombre del lote");
    expect(nameInput.value).toBe("");
    expect(screen.queryByText("Ensayo.pdf")).toBeNull();
  });

  it("si todavía se envían archivos, al volver se sigue viendo su avance", async () => {
    submitMock.mockReturnValue(new Promise(() => undefined));
    const { rerender } = render(page("visible"));
    fillForm([pdf("Ensayo.pdf")]);
    submit();
    await waitFor(() => expect(submitMock).toHaveBeenCalledTimes(1));

    await act(async () => rerender(page("hidden")));
    await act(async () => rerender(page("visible")));

    expect(screen.getByText("Ensayo.pdf")).toBeTruthy();
    expect(screen.queryByLabelText("Nombre del lote")).toBeNull();
  });

  it("el botón sigue inactivo hasta que hay un archivo válido", () => {
    render(<NewBatchForm />);

    expect(screen.queryByRole("button", { name: /Analizar lote/ })).toBeNull();

    fillForm([new File(["hola"], "notas.txt", { type: "text/plain" })]);

    const button = screen.getByRole<HTMLButtonElement>("button", { name: /Analizar lote/ });
    expect(button.disabled).toBe(true);
    expect(button.textContent).toContain("0 archivos");
  });

  it("no crea el lote si el nombre o el periodo solo tienen espacios", () => {
    render(<NewBatchForm />);

    fillForm([pdf("Ensayo.pdf")], "   ");
    submit();

    expect(screen.getByRole("alert").textContent).toContain("nombre y el periodo");
    expect(createMock).not.toHaveBeenCalled();
  });

  it("crea el lote con los datos limpios y envía solo los archivos válidos, en orden", async () => {
    submitMock.mockResolvedValue({ kind: "created", analysisId: "a1" });
    render(<NewBatchForm />);

    fillForm(
      [
        pdf("Ensayo_A.pdf"),
        new File(["hola"], "notas.txt", { type: "text/plain" }),
        pdf("Ensayo_B.pdf"),
      ],
      "  Metodología 5B ",
      " 2026-2S ",
    );
    submit();

    await waitFor(() => expect(submitMock).toHaveBeenCalledTimes(2));
    expect(createMock).toHaveBeenCalledWith("Metodología 5B", "2026-2S", expect.any(Function));
    expect(submitMock.mock.calls.map(([, file]) => file.name)).toEqual([
      "Ensayo_A.pdf",
      "Ensayo_B.pdf",
    ]);
    expect(submitMock.mock.calls[0][0]).toBe("lote-1");

    // El archivo rechazado sigue a la vista, con su motivo, aunque no se envió.
    const rejected = rowOf("notas.txt");
    expect(rejected.textContent).toContain("Solo se aceptan archivos PDF.");
    expect(rejected.textContent).toContain("No enviado");
    await waitFor(() => expect(rowOf("Ensayo_B.pdf").textContent).toContain("En cola"));
  });

  it("si el lote no se puede crear, muestra el motivo y conserva la selección", async () => {
    createMock.mockResolvedValueOnce({ kind: "error", message: "Solo para docentes." });
    render(<NewBatchForm />);

    fillForm([pdf("Ensayo_A.pdf")]);
    submit();

    expect((await screen.findByRole("alert")).textContent).toBe("Solo para docentes.");
    expect(screen.getByText("Ensayo_A.pdf")).toBeTruthy();
    expect(submitMock).not.toHaveBeenCalled();

    submit();

    await waitFor(() => expect(createMock).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(submitMock).toHaveBeenCalledTimes(1));
  });

  it("el error de un archivo no detiene a los demás y se marca con su motivo", async () => {
    submitMock
      .mockResolvedValueOnce({ kind: "error", message: "El archivo está dañado." })
      .mockResolvedValueOnce({ kind: "created", analysisId: "a2" })
      .mockResolvedValueOnce({ kind: "duplicate", analysisId: "a2", finished: false });
    render(<NewBatchForm />);

    fillForm([pdf("Ensayo_A.pdf"), pdf("Ensayo_B.pdf"), pdf("Copia_de_B.pdf")]);
    submit();

    await waitFor(() =>
      expect(rowOf("Copia_de_B.pdf").textContent).toContain("Ya está en el lote"),
    );
    expect(rowOf("Ensayo_A.pdf").textContent).toContain("El archivo está dañado.");
    expect(rowOf("Ensayo_A.pdf").textContent).toContain("No enviado");
    expect(rowOf("Ensayo_B.pdf").textContent).toContain("En cola");
  });

  it("reintentar envía solo los que fallaron y al mismo lote", async () => {
    submitMock
      .mockResolvedValueOnce({ kind: "error", message: "Sin conexión." })
      .mockResolvedValueOnce({ kind: "created", analysisId: "a2" })
      .mockResolvedValueOnce({ kind: "created", analysisId: "a1" });
    render(<NewBatchForm />);

    fillForm([pdf("Ensayo_A.pdf"), pdf("Ensayo_B.pdf")]);
    submit();

    const retry = await screen.findByRole("button", { name: /Reintentar el archivo/ });
    fireEvent.click(retry);

    await waitFor(() => expect(submitMock).toHaveBeenCalledTimes(3));
    expect(submitMock.mock.calls[2][0]).toBe("lote-1");
    expect(submitMock.mock.calls[2][1].name).toBe("Ensayo_A.pdf");
    expect(createMock).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(screen.queryByRole("button", { name: /Reintentar/ })).toBeNull());
  });

  it("mientras se envía oculta el tablero y avisa; al terminar lo ofrece", async () => {
    let finish: (value: { kind: "created"; analysisId: string }) => void = () => undefined;
    submitMock.mockReturnValueOnce(
      new Promise((resolve) => {
        finish = resolve;
      }),
    );
    render(<NewBatchForm />);

    fillForm([pdf("Ensayo_A.pdf")]);
    submit();

    expect((await screen.findByText(/Enviando 1 de 1/)).textContent).toContain("página abierta");
    expect(screen.queryByRole("link", { name: /tablero/ })).toBeNull();
    expect(rowOf("Ensayo_A.pdf").textContent).toContain("Subiendo");

    await act(async () => finish({ kind: "created", analysisId: "a1" }));

    expect(screen.queryByText(/Enviando/)).toBeNull();
    expect(screen.getByRole("link", { name: /tablero/ }).getAttribute("href")).toBe(
      "/docente/lotes/lote-1",
    );
  });

  it("consulta el avance hasta que cada análisis termina, con su resultado o su motivo", async () => {
    vi.useFakeTimers();
    submitMock
      .mockResolvedValueOnce({ kind: "created", analysisId: "a1" })
      .mockResolvedValueOnce({ kind: "created", analysisId: "a2" });
    progressMock.mockResolvedValueOnce([
      {
        analysisId: "a1",
        status: "verificando",
        progress: 95,
        totalReferences: 22,
        errorMessage: null,
      },
      { analysisId: "a2", status: "error", progress: 0, totalReferences: null, errorMessage: null },
    ]);
    progressMock.mockResolvedValueOnce([
      {
        analysisId: "a1",
        status: "completado",
        progress: 100,
        totalReferences: 22,
        errorMessage: null,
      },
      { analysisId: "a2", status: "error", progress: 0, totalReferences: null, errorMessage: null },
    ]);
    render(<NewBatchForm />);

    fillForm([pdf("Ensayo_A.pdf"), pdf("Ensayo_B.pdf")]);
    submit();
    await act(async () => vi.advanceTimersByTimeAsync(0));

    await act(async () => vi.advanceTimersByTimeAsync(POLL_MS));
    expect(rowOf("Ensayo_A.pdf").textContent).toContain("Verificando 22/22");
    expect(rowOf("Ensayo_B.pdf").textContent).toContain("El análisis no pudo completarse.");

    await act(async () => vi.advanceTimersByTimeAsync(POLL_MS));
    expect(rowOf("Ensayo_A.pdf").textContent).toContain("Listo");
    expect(screen.getByRole("heading", { level: 2 }).textContent).toContain("1 analizado");

    // Todo terminó: no se vuelve a consultar.
    await act(async () => vi.advanceTimersByTimeAsync(POLL_MS * 3));
    expect(progressMock).toHaveBeenCalledTimes(2);
  });
});
