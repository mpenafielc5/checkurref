import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { compareEngines } from "../api";
import type { EngineOutput, LabComparison } from "../types";
import { EngineComparison } from "./engine-comparison";

vi.mock("../api", () => ({ compareEngines: vi.fn() }));

const compareMock = vi.mocked(compareEngines);

const REFERENCE = "Pérez, M. (2021). Redes neuronales. Revista Andina, 14(2), 45-60.";

const ANYSTYLE: EngineOutput = {
  engine: "anystyle",
  elapsedMs: 12,
  error: null,
  fields: { autores: "Pérez, M.", anio: "2021", titulo: "Redes neuronales", contenedor: "Andina" },
};
const SPACY: EngineOutput = {
  engine: "spacy",
  elapsedMs: 48,
  error: null,
  fields: { autores: "Pérez, M.", anio: "2021", titulo: "Redes", contenedor: null },
};
const RESULT: LabComparison = {
  engines: [ANYSTYLE, SPACY],
  differentFields: ["titulo", "contenedor"],
  comparedFields: 4,
  matchingFields: 2,
};

function write(text: string) {
  fireEvent.change(screen.getByLabelText("Referencia de prueba"), { target: { value: text } });
}

function button(): HTMLButtonElement {
  return screen.getByRole<HTMLButtonElement>("button");
}

async function compare(result: LabComparison = RESULT) {
  compareMock.mockResolvedValue({ kind: "ready", comparison: result });
  write(REFERENCE);
  fireEvent.click(button());
  await screen.findByText(/Concordancia|Sin el resultado|Ningún motor/);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("EngineComparison", () => {
  it("no compara un texto demasiado corto para ser una referencia", () => {
    render(<EngineComparison />);

    expect(button().disabled).toBe(true);
    write("   corto   ");
    expect(button().disabled).toBe(true);
    write(REFERENCE);
    expect(button().disabled).toBe(false);
  });

  it("envía el texto limpio y muestra los campos de cada motor lado a lado", async () => {
    render(<EngineComparison />);

    await compare();

    expect(compareMock).toHaveBeenCalledWith(REFERENCE, expect.any(Function));
    const anystyle = within(screen.getByRole("region", { name: "AnyStyle (CRF)" }));
    const spacy = within(screen.getByRole("region", { name: "spaCy + reglas" }));
    expect(anystyle.getByText("Redes neuronales")).toBeTruthy();
    expect(spacy.getByText("Redes")).toBeTruthy();
    expect(anystyle.getByText("12 ms")).toBeTruthy();
    expect(screen.getByText("Concordancia: 2 de 4 campos")).toBeTruthy();
  });

  it("resalta en ambos motores los campos que no coinciden, con texto además del color", async () => {
    render(<EngineComparison />);

    await compare();

    const spacy = within(screen.getByRole("region", { name: "spaCy + reglas" }));
    expect(screen.getAllByText("No coincide")).toHaveLength(4);
    const title = spacy.getByText("Título").closest("div");
    expect(title?.textContent).toContain("No coincide");
    expect(title?.className).toContain("bg-verdict-discrepancy-soft");
    const year = spacy.getByText("Año").closest("div");
    expect(year?.textContent).not.toContain("No coincide");
    expect(year?.className).not.toContain("bg-verdict-discrepancy-soft");
    expect(spacy.getByText("No detectado")).toBeTruthy();
  });

  it("si un motor falla, lo dice y muestra la salida del otro sin reemplazarlo", async () => {
    const failed: EngineOutput = {
      engine: "anystyle",
      elapsedMs: 0,
      error: "No se encontró el comando.",
      fields: null,
    };
    render(<EngineComparison />);

    await compare({ ...RESULT, engines: [failed, SPACY], differentFields: [], matchingFields: 4 });

    const anystyle = within(screen.getByRole("region", { name: "AnyStyle (CRF)" }));
    expect(anystyle.getByRole("alert").textContent).toContain("No se encontró el comando.");
    expect(anystyle.queryByText("Año")).toBeNull();
    expect(
      within(screen.getByRole("region", { name: "spaCy + reglas" })).getByText("Redes"),
    ).toBeTruthy();
    expect(screen.getByText(/no hay concordancia que calcular/)).toBeTruthy();
  });

  it("si cambia el texto, el resultado anterior desaparece", async () => {
    render(<EngineComparison />);
    await compare();

    write(`${REFERENCE} Otra.`);

    expect(screen.queryByText(/Concordancia/)).toBeNull();
  });

  it("si la petición falla, muestra el motivo y conserva el texto", async () => {
    compareMock.mockResolvedValue({ kind: "error", message: "Sin conexión." });
    render(<EngineComparison />);

    write(REFERENCE);
    fireEvent.click(button());

    expect((await screen.findByRole("alert")).textContent).toBe("Sin conexión.");
    expect(screen.getByLabelText<HTMLTextAreaElement>("Referencia de prueba").value).toBe(
      REFERENCE,
    );
  });
});
