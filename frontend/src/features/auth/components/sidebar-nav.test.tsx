import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { navItemsForRole } from "../rules";
import { SidebarNav } from "./sidebar-nav";

const route = vi.hoisted(() => ({ pathname: "/estudiante/trabajos/123" }));

vi.mock("next/navigation", () => ({
  usePathname: () => route.pathname,
}));

describe("SidebarNav", () => {
  it("contraída, cada opción conserva su nombre para los lectores de pantalla", () => {
    render(<SidebarNav items={navItemsForRole("docente")} homeHref="/docente" />);

    for (const label of ["Inicio", "Lotes", "Ayuda"]) {
      expect(screen.getByRole("link", { name: label })).toBeTruthy();
    }
  });

  it("marca la sección actual y no Inicio", () => {
    render(<SidebarNav items={navItemsForRole("estudiante")} homeHref="/estudiante" />);

    expect(screen.getByRole("link", { name: "Mis trabajos" }).getAttribute("aria-current")).toBe(
      "page",
    );
    expect(screen.getByRole("link", { name: "Inicio" }).getAttribute("aria-current")).toBeNull();
  });
});
