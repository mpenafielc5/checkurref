import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { deleteWork, interpretDeleteResponse } from "@/shared/lib/work-deletion";
import { DeleteWorkButton } from "./delete-work-button";

vi.mock("@/shared/lib/work-deletion", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/shared/lib/work-deletion")>();
  return { ...original, deleteWork: vi.fn() };
});

const deleteMock = vi.mocked(deleteWork);

beforeEach(() => {
  vi.clearAllMocks();
  // jsdom no siempre abre el elemento dialog: basta con marcarlo como abierto.
  HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
});

function renderButton(onDeleted = vi.fn()) {
  render(<DeleteWorkButton analysisId="a1" fileName="Avance_2.pdf" onDeleted={onDeleted} />);
  return onDeleted;
}

describe("interpretDeleteResponse", () => {
  it("204 y 404 dejan el trabajo eliminado; lo demás trae el motivo de la API", () => {
    expect(interpretDeleteResponse(204, null)).toEqual({ kind: "deleted" });
    expect(interpretDeleteResponse(404, { detail: "No se encontró el análisis." })).toEqual({
      kind: "deleted",
    });
    expect(interpretDeleteResponse(409, { detail: "El análisis aún no termina." })).toEqual({
      kind: "error",
      message: "El análisis aún no termina.",
    });
    expect(interpretDeleteResponse(500, null).kind).toBe("error");
  });
});

describe("DeleteWorkButton", () => {
  it("pide confirmar, elimina el trabajo y avisa a la lista", async () => {
    deleteMock.mockResolvedValue({ kind: "deleted" });
    const onDeleted = renderButton();

    fireEvent.click(screen.getByRole("button", { name: "Eliminar Avance_2.pdf" }));
    const dialog = within(screen.getByRole("dialog"));
    expect(dialog.getByText(/no se puede deshacer/)).toBeTruthy();
    expect(deleteMock).not.toHaveBeenCalled();

    fireEvent.click(dialog.getByRole("button", { name: "Eliminar trabajo" }));

    await waitFor(() => expect(onDeleted).toHaveBeenCalledTimes(1));
    expect(deleteMock).toHaveBeenCalledWith("a1");
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("el botón de confirmar es rojo y cancelar no elimina", () => {
    const onDeleted = renderButton();

    fireEvent.click(screen.getByRole("button", { name: "Eliminar Avance_2.pdf" }));
    const dialog = within(screen.getByRole("dialog"));
    expect(dialog.getByRole("button", { name: "Eliminar trabajo" }).className).toContain(
      "bg-danger",
    );
    fireEvent.click(dialog.getByRole("button", { name: "Cancelar" }));

    expect(screen.queryByRole("dialog")).toBeNull();
    expect(deleteMock).not.toHaveBeenCalled();
    expect(onDeleted).not.toHaveBeenCalled();
  });

  it("si no se puede eliminar, muestra el motivo sin cerrar el diálogo", async () => {
    deleteMock.mockResolvedValue({ kind: "error", message: "El análisis aún no termina." });
    const onDeleted = renderButton();

    fireEvent.click(screen.getByRole("button", { name: "Eliminar Avance_2.pdf" }));
    fireEvent.click(screen.getByRole("button", { name: "Eliminar trabajo" }));

    expect((await screen.findByRole("alert")).textContent).toBe("El análisis aún no termina.");
    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(onDeleted).not.toHaveBeenCalled();
  });
});
