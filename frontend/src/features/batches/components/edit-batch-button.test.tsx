import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { updateBatch } from "../api";
import { EditBatchButton } from "./edit-batch-button";

vi.mock("../api", () => ({ updateBatch: vi.fn() }));

const updateMock = vi.mocked(updateBatch);
const BATCH = { id: "lote-1", name: "Metodología 5B", period: "2026-2S" };

beforeEach(() => {
  vi.clearAllMocks();
  HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
});

function openDialog(onSaved = vi.fn()) {
  render(<EditBatchButton batch={BATCH} onSaved={onSaved} />);
  fireEvent.click(screen.getByRole("button", { name: "Editar" }));
  return { dialog: within(screen.getByRole("dialog")), onSaved };
}

describe("EditBatchButton", () => {
  it("muestra los datos actuales y guarda los nuevos sin espacios sobrantes", async () => {
    updateMock.mockResolvedValue({ kind: "updated" });
    const { dialog, onSaved } = openDialog();

    expect(dialog.getByLabelText<HTMLInputElement>("Nombre del lote").value).toBe("Metodología 5B");
    fireEvent.change(dialog.getByLabelText("Nombre del lote"), {
      target: { value: "  Metodología 5C " },
    });
    fireEvent.change(dialog.getByLabelText("Periodo"), { target: { value: " Semana 1 " } });
    fireEvent.click(dialog.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    expect(updateMock).toHaveBeenCalledWith("lote-1", "Metodología 5C", "Semana 1");
  });

  it("no guarda si el nombre o el periodo quedan vacíos", () => {
    const { dialog } = openDialog();

    fireEvent.change(dialog.getByLabelText("Periodo"), { target: { value: "   " } });
    fireEvent.click(dialog.getByRole("button", { name: "Guardar cambios" }));

    expect(dialog.getByRole("alert").textContent).toContain("nombre y el periodo");
    expect(updateMock).not.toHaveBeenCalled();
  });

  it("si la API falla, muestra el motivo y conserva lo escrito", async () => {
    updateMock.mockResolvedValue({ kind: "error", message: "No se encontró el lote." });
    const { dialog, onSaved } = openDialog();

    fireEvent.change(dialog.getByLabelText("Nombre del lote"), { target: { value: "Otro" } });
    fireEvent.click(dialog.getByRole("button", { name: "Guardar cambios" }));

    expect((await dialog.findByRole("alert")).textContent).toBe("No se encontró el lote.");
    expect(dialog.getByLabelText<HTMLInputElement>("Nombre del lote").value).toBe("Otro");
    expect(onSaved).not.toHaveBeenCalled();
  });
});
