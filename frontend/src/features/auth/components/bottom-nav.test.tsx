import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { navItemsForRole } from "../rules";
import { BottomNav } from "./bottom-nav";

vi.mock("next/navigation", () => ({
  usePathname: () => "/admin/usuarios",
}));

describe("BottomNav", () => {
  it("muestra las opciones del rol con su texto y marca la actual", () => {
    render(
      <BottomNav
        items={navItemsForRole("admin")}
        homeHref="/admin"
        account={{ href: "/admin/cuenta", avatar: <span>AT</span> }}
      />,
    );

    expect(screen.getByRole("link", { name: "Usuarios" }).getAttribute("aria-current")).toBe(
      "page",
    );
    expect(screen.getByRole("link", { name: "Inicio" }).getAttribute("aria-current")).toBeNull();
    expect(screen.getByRole("link", { name: "Laboratorio" })).toBeTruthy();
    expect(screen.getByRole("link", { name: /Cuenta/ }).getAttribute("href")).toBe("/admin/cuenta");
  });
});
