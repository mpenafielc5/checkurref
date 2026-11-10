import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { deleteBatch } from "../api";
import { DeleteBatchButton } from "./delete-batch-button";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("../api", () => ({ deleteBatch: vi.fn() }));

const deleteMock = vi.mocked(deleteBatch);
const BATCH = { id: "lote-1", name: "Metodología 5B", totalWorks: 3, inProgress: 0 };

beforeEach(() => {
  vi.clearAllMocks();
  HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
});

describe("DeleteBatchButton", () => {
  it("avisa cuántos trabajos se pierden, elimina el lote y vuelve a la lista", async () => {
    deleteMock.mockResolvedValue({ kind: "deleted" });
    render(<DeleteBatchButton batch={BATCH} />);

    fireEvent.click(screen.getByRole("button", { name: "Eliminar lote" }));
    const dialog = within(screen.getByRole("dialog"));
    expect(dialog.getByText(/sus 3 trabajos, con sus PDF y sus informes/)).toBeTruthy();
    fireEvent.click(dialog.getByRole("button", { name: "Eliminar lote" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/docente/lotes"));
    expect(deleteMock).toHaveBeenCalledWith("lote-1");
  });

  it("con un solo trabajo lo dice en singular", () => {
    render(<DeleteBatchButton batch={{ ...BATCH, totalWorks: 1 }} />);

    fireEvent.click(screen.getByRole("button", { name: "Eliminar lote" }));

    expect(screen.getByText(/Se eliminará su único trabajo, con su PDF y su informe/)).toBeTruthy();
  });

  it("con trabajos en análisis el botón queda desactivado", () => {
    render(<DeleteBatchButton batch={{ ...BATCH, inProgress: 1 }} />);

    const button = screen.getByRole<HTMLButtonElement>("button", { name: "Eliminar lote" });
    expect(button.disabled).toBe(true);
    expect(button.title).toContain("cuando terminen");
  });

  it("si no se puede eliminar, muestra el motivo y no sale del tablero", async () => {
    deleteMock.mockResolvedValue({
      kind: "error",
      message: "Hay trabajos del lote que aún se analizan.",
    });
    render(<DeleteBatchButton batch={BATCH} />);

    fireEvent.click(screen.getByRole("button", { name: "Eliminar lote" }));
    fireEvent.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: "Eliminar lote" }),
    );

    expect((await screen.findByRole("alert")).textContent).toContain("aún se analizan");
    expect(push).not.toHaveBeenCalled();
  });
});
