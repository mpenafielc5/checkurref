import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import HomePage from "./page";

describe("HomePage", () => {
  it("muestra la propuesta de valor como título principal", () => {
    render(<HomePage />);
    expect(
      screen.getByRole("heading", { level: 1, name: "¿Tus referencias existen de verdad?" }),
    ).toBeDefined();
  });

  it("usa las regiones semánticas de la página", () => {
    render(<HomePage />);
    expect(screen.getByRole("banner")).toBeDefined();
    expect(screen.getByRole("main")).toBeDefined();
    expect(screen.getByRole("contentinfo")).toBeDefined();
  });

  it("ofrece el acceso con la cuenta institucional", () => {
    render(<HomePage />);
    expect(screen.getByRole("heading", { name: "Ingresar" })).toBeDefined();
    expect(screen.getByRole("button", { name: /Continuar con Google/ })).toBeDefined();
  });

  it("explica los cinco veredictos", () => {
    render(<HomePage />);
    const verdicts = screen.getByRole("list", { name: "Veredictos" });
    expect(verdicts.querySelectorAll("li")).toHaveLength(5);
  });
});
