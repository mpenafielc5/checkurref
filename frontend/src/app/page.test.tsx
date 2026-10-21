import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import HomePage from "./page";

describe("HomePage", () => {
  it("muestra el título principal", () => {
    render(<HomePage />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Auditoría de referencias bibliográficas" }),
    ).toBeDefined();
  });

  it("usa las regiones semánticas de la página", () => {
    render(<HomePage />);
    expect(screen.getByRole("banner")).toBeDefined();
    expect(screen.getByRole("main")).toBeDefined();
    expect(screen.getByRole("contentinfo")).toBeDefined();
  });
});
