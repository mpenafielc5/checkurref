import { act, fireEvent, render, screen } from "@testing-library/react";
import { Activity } from "react";
import { describe, expect, it, vi } from "vitest";
import { submitDocument } from "../api";
import { StudentUpload } from "./student-upload";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("../api", () => ({
  submitDocument: vi.fn(),
  wakeApi: vi.fn(),
}));

const PDF = new File(["%PDF-1.7"], "Trabajo_final.pdf", { type: "application/pdf" });

function choose(file: File) {
  const input = document.querySelector<HTMLInputElement>('input[type="file"]');
  if (!input) throw new Error("Falta el campo de archivo");
  fireEvent.change(input, { target: { files: [file] } });
}

function page(mode: "visible" | "hidden") {
  return (
    <Activity mode={mode}>
      <StudentUpload />
    </Activity>
  );
}

describe("StudentUpload", () => {
  it("al volver a la página empieza de cero y no se queda en Subiendo", async () => {
    // La subida no termina: la pantalla queda en "Subiendo…" cuando se navega a otra.
    vi.mocked(submitDocument).mockReturnValue(new Promise(() => undefined));
    const { rerender } = render(page("visible"));

    choose(PDF);
    fireEvent.click(screen.getByRole("button", { name: "Analizar referencias" }));
    expect(screen.getByRole("button", { name: "Subiendo…" })).toBeTruthy();

    // Next.js oculta la página con Activity al navegar y la vuelve a mostrar al regresar.
    await act(async () => rerender(page("hidden")));
    await act(async () => rerender(page("visible")));

    expect(screen.queryByRole("button", { name: "Subiendo…" })).toBeNull();
    expect(screen.queryByText("Trabajo_final.pdf")).toBeNull();
    expect(screen.getByText("Arrastra aquí el PDF de tu trabajo")).toBeTruthy();
  });

  it("un PDF que la API rechaza deja la zona vacía y explica cuál y por qué", async () => {
    vi.mocked(submitDocument).mockResolvedValue({
      kind: "error",
      message: "No se encontró la sección de referencias.",
      rejected: true,
    });
    render(page("visible"));

    choose(PDF);
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Analizar referencias" }));
    });

    expect(screen.getByRole("alert").textContent).toBe(
      "Trabajo_final.pdf: No se encontró la sección de referencias.",
    );
    expect(screen.getByText("Arrastra aquí el PDF de tu trabajo")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Analizar referencias" })).toBeNull();
  });

  it("una falla de conexión conserva el archivo para reintentar", async () => {
    vi.mocked(submitDocument).mockResolvedValue({ kind: "error", message: "Sin conexión." });
    render(page("visible"));

    choose(PDF);
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Analizar referencias" }));
    });

    expect(screen.getByRole("alert").textContent).toBe("Sin conexión.");
    expect(screen.getByText("Trabajo_final.pdf")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Analizar referencias" })).toHaveProperty(
      "disabled",
      false,
    );
  });
});
