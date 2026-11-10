import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchUsers, updateUser } from "../api";
import type { UserRow, UsersPage } from "../types";
import { UserTable } from "./user-table";

const route = vi.hoisted(() => ({
  search: "",
  replace: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/admin/usuarios",
  useSearchParams: () => new URLSearchParams(route.search),
}));

vi.mock("../api", () => ({
  fetchUsers: vi.fn(),
  updateUser: vi.fn(),
}));

const fetchMock = vi.mocked(fetchUsers);
const updateMock = vi.mocked(updateUser);

const STUDENT: UserRow = {
  id: "u1",
  name: "ANA TORRES",
  email: "atorres@ejemplo.test",
  role: "estudiante",
  active: true,
};
const TEACHER: UserRow = {
  id: "u2",
  name: "Luis Vera",
  email: "lvera@ejemplo.test",
  role: "docente",
  active: false,
};
const ADMIN: UserRow = {
  id: "u3",
  name: "Paola Rivas",
  email: "privas@ejemplo.test",
  role: "admin",
  active: true,
};

function page(items: UserRow[]): UsersPage {
  return {
    slice: { items, page: 1, totalPages: 1, total: items.length, first: 1, last: items.length },
    counts: { todos: 3, estudiante: 1, docente: 1, admin: 1 },
  };
}

function table() {
  return within(screen.getByRole("table"));
}

async function renderUsers(items: UserRow[] = [STUDENT, TEACHER, ADMIN]) {
  fetchMock.mockResolvedValue({ kind: "ready", users: page(items) });
  render(<UserTable />);
  await screen.findByRole("table");
}

beforeEach(() => {
  vi.clearAllMocks();
  route.search = "";
  vi.spyOn(window.history, "replaceState").mockImplementation((_data, _unused, url) =>
    route.replace(url),
  );
  // jsdom no siempre abre el elemento dialog: basta con marcarlo como abierto.
  HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
});

afterEach(() => {
  vi.useRealTimers();
});

describe("UserTable", () => {
  it("muestra el nombre legible, el rol, el estado y los totales por rol", async () => {
    await renderUsers();

    expect(table().getByText("Ana Torres")).toBeTruthy();
    expect(table().getByText("Inactivo")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Estudiantes 1/ })).toBeTruthy();
  });

  it("no ofrece acciones sobre una cuenta de administrador, incluida la propia", async () => {
    await renderUsers();

    expect(table().getByText("Sin acciones")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /privas@ejemplo.test/ })).toBeNull();
  });

  it("el cambio de rol no se aplica sin confirmar", async () => {
    await renderUsers();

    fireEvent.click(table().getByRole("button", { name: /Cambiar el rol de atorres/ }));

    const dialog = within(screen.getByRole("dialog"));
    expect(dialog.getByRole("heading", { name: "¿Cambiar a Docente?" })).toBeTruthy();
    expect(updateMock).not.toHaveBeenCalled();

    fireEvent.click(dialog.getByRole("button", { name: "Cancelar" }));

    expect(screen.queryByRole("dialog")).toBeNull();
    expect(updateMock).not.toHaveBeenCalled();
  });

  it("al confirmar el rol, lo aplica y vuelve a consultar la lista", async () => {
    updateMock.mockResolvedValue({ kind: "updated" });
    await renderUsers();
    expect(fetchMock).toHaveBeenCalledTimes(1);

    fireEvent.click(table().getByRole("button", { name: /Cambiar el rol de atorres/ }));
    fireEvent.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: "Cambiar a Docente" }),
    );

    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(updateMock).toHaveBeenCalledWith("u1", { kind: "role", role: "docente" });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  });

  it("desactivar avisa que los trabajos se conservan", async () => {
    updateMock.mockResolvedValue({ kind: "updated" });
    await renderUsers();

    fireEvent.click(table().getByRole("button", { name: /Desactivar la cuenta de atorres/ }));
    const dialog = within(screen.getByRole("dialog"));
    expect(dialog.getByText(/no podrá iniciar sesión. Sus trabajos se conservan/)).toBeTruthy();
    expect(dialog.getByRole("button", { name: "Desactivar cuenta" }).className).toContain(
      "bg-danger",
    );

    fireEvent.click(dialog.getByRole("button", { name: "Desactivar cuenta" }));

    await waitFor(() =>
      expect(updateMock).toHaveBeenCalledWith("u1", { kind: "active", active: false }),
    );
  });

  it("reactivar se confirma con el botón verde y cambiar el rol con el principal", async () => {
    await renderUsers();

    fireEvent.click(table().getByRole("button", { name: /Reactivar la cuenta de lvera/ }));
    const reactivate = within(screen.getByRole("dialog"));
    expect(reactivate.getByRole("button", { name: "Reactivar cuenta" }).className).toContain(
      "bg-restore",
    );
    fireEvent.click(reactivate.getByRole("button", { name: "Cancelar" }));

    fireEvent.click(table().getByRole("button", { name: /Cambiar el rol de atorres/ }));
    const role = within(screen.getByRole("dialog"));
    expect(role.getByRole("button", { name: "Cambiar a Docente" }).className).toContain(
      "bg-action",
    );
  });

  it("desactivar se pone rojo y reactivar verde, únicamente al pasar el cursor", async () => {
    await renderUsers();

    const deactivate = table().getByRole("button", { name: /Desactivar la cuenta de atorres/ });
    const reactivate = table().getByRole("button", { name: /Reactivar la cuenta de lvera/ });
    const role = table().getByRole("button", { name: /Cambiar el rol de atorres/ });
    expect(deactivate.className).toContain("hover:bg-danger");
    expect(deactivate.className).toContain("text-ink");
    expect(reactivate.className).toContain("hover:bg-restore");
    expect(reactivate.className).toContain("text-ink");
    expect(reactivate.className).not.toContain("danger");
    expect(role.className).not.toContain("danger");
  });

  it("al cancelar, el foco vuelve al botón que abrió el diálogo", async () => {
    await renderUsers();
    const opener = table().getByRole("button", { name: /Cambiar el rol de atorres/ });

    opener.focus();
    fireEvent.click(opener);
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Cancelar" }));

    expect(document.activeElement).toBe(opener);
  });

  it("la reactivación también requiere confirmación", async () => {
    updateMock.mockResolvedValue({ kind: "updated" });
    await renderUsers();

    fireEvent.click(table().getByRole("button", { name: /Reactivar la cuenta de lvera/ }));
    expect(updateMock).not.toHaveBeenCalled();

    fireEvent.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: "Reactivar cuenta" }),
    );

    await waitFor(() =>
      expect(updateMock).toHaveBeenCalledWith("u2", { kind: "active", active: true }),
    );
  });

  it("si la API rechaza el cambio, muestra el motivo y no vuelve a consultar", async () => {
    updateMock.mockResolvedValue({ kind: "error", message: "No se permite este cambio." });
    await renderUsers();

    fireEvent.click(table().getByRole("button", { name: /Cambiar el rol de atorres/ }));
    const dialog = within(screen.getByRole("dialog"));
    fireEvent.click(dialog.getByRole("button", { name: "Cambiar a Docente" }));

    expect((await dialog.findByRole("alert")).textContent).toBe("No se permite este cambio.");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("la búsqueda espera a que termine de escribir y vuelve a la primera página", async () => {
    route.search = "pagina=3";
    await renderUsers();
    vi.useFakeTimers();

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: " torres " } });

    expect(route.replace).not.toHaveBeenCalled();
    await act(async () => vi.advanceTimersByTimeAsync(400));
    expect(route.replace).toHaveBeenCalledWith("/admin/usuarios?buscar=torres");
  });

  it("al escribir seguido hace una sola búsqueda, con el texto completo", async () => {
    await renderUsers();
    vi.useFakeTimers();
    const box = screen.getByRole("searchbox");

    for (const text of ["t", "to", "tor", "torr", "torre", "torres"]) {
      fireEvent.change(box, { target: { value: text } });
      await act(async () => vi.advanceTimersByTimeAsync(150));
    }
    expect(route.replace).not.toHaveBeenCalled();

    await act(async () => vi.advanceTimersByTimeAsync(400));
    expect(route.replace).toHaveBeenCalledTimes(1);
    expect(route.replace).toHaveBeenCalledWith("/admin/usuarios?buscar=torres");
  });

  it("consulta con la página, la búsqueda y el rol de la dirección", async () => {
    route.search = "pagina=2&buscar=vera&rol=docente";
    await renderUsers();

    expect(fetchMock).toHaveBeenCalledWith(2, "vera", "docente", expect.any(Function));
  });

  it("elegir un rol cambia la dirección y quita la página", async () => {
    route.search = "pagina=2";
    await renderUsers();

    fireEvent.click(screen.getByRole("button", { name: /Docentes/ }));

    expect(route.replace).toHaveBeenCalledWith("/admin/usuarios?rol=docente");
  });

  it("si la lista no carga, muestra el motivo", async () => {
    fetchMock.mockResolvedValue({ kind: "error", message: "No se pudo cargar." });
    render(<UserTable />);

    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo cargar.");
  });
});
