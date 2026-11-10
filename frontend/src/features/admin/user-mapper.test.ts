import { describe, expect, it } from "vitest";
import { toUsersPage } from "./user-mapper";

const USER = {
  id: "u1",
  name: "Ana Torres",
  email: "atorres@ejemplo.test",
  role: "docente",
  active: true,
  created_at: "2026-11-06T10:00:00Z",
};

const BODY = {
  items: [USER, { ...USER, id: "u2" }],
  page: 2,
  page_size: 20,
  total: 22,
  total_pages: 2,
  counts: { todos: 22, estudiante: 20, docente: 2, admin: 0 },
};

describe("toUsersPage", () => {
  it("traduce la página con el rango mostrado y los totales", () => {
    const users = toUsersPage(BODY);

    expect(users?.slice.first).toBe(21);
    expect(users?.slice.last).toBe(22);
    expect(users?.counts.docente).toBe(2);
    expect(users?.slice.items[0]).toEqual({
      id: "u1",
      name: "Ana Torres",
      email: "atorres@ejemplo.test",
      role: "docente",
      active: true,
    });
  });

  it("una página vacía no inventa un rango", () => {
    const users = toUsersPage({ ...BODY, items: [], total: 0, page: 1 });

    expect(users?.slice.first).toBe(0);
    expect(users?.slice.last).toBe(0);
  });

  it("una respuesta inesperada devuelve null", () => {
    expect(toUsersPage({ ...BODY, items: [{ ...USER, role: "rector" }] })).toBeNull();
    expect(toUsersPage(null)).toBeNull();
  });
});
