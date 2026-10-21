import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PageSection } from "./page-section";

describe("PageSection", () => {
  it("en una pantalla de detalle, enlaza a la pantalla de nivel superior", () => {
    render(
      <PageSection
        title="Diagnóstico de veracidad"
        back={{ href: "/estudiante/trabajos", label: "Mis trabajos" }}
      />,
    );
    expect(screen.getByRole("link", { name: "Volver a Mis trabajos" }).getAttribute("href")).toBe(
      "/estudiante/trabajos",
    );
  });

  it("sin `back`, no muestra el enlace", () => {
    render(<PageSection title="Inicio" />);
    expect(screen.queryByRole("link")).toBeNull();
  });
});
