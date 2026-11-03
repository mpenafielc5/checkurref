import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { CorrectedReference } from "../types";
import { COPIED_MS, CorrectedReferencePanel } from "./corrected-reference";

const CORRECTED: CorrectedReference = {
  text: "Pérez, M. (2021). Redes. Revista Andina, 8(1), 10-25.",
  segments: [
    { text: "Pérez, M. (", italic: false, changed: false },
    { text: "2021", italic: false, changed: true },
    { text: "). Redes. ", italic: false, changed: false },
    { text: "Revista Andina, 8", italic: true, changed: false },
    { text: "(1), 10-25.", italic: false, changed: false },
  ],
};

function mockClipboard(writeText: (text: string) => Promise<void>) {
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
}

afterEach(() => {
  vi.useRealTimers();
});

describe("CorrectedReferencePanel", () => {
  it("resalta lo que cambió y pone en cursiva lo que corresponde", () => {
    render(<CorrectedReferencePanel corrected={CORRECTED} />);

    expect(screen.getByText("2021").tagName).toBe("MARK");
    expect(screen.getByText("Revista Andina, 8").tagName).toBe("I");
  });

  it("tiene el nombre accesible que pide la historia", () => {
    render(<CorrectedReferencePanel corrected={CORRECTED} />);

    expect(screen.getByRole("button", { name: "Copiar referencia corregida" })).toBeTruthy();
  });

  it("copia el texto y muestra Copiada durante 2 s", async () => {
    vi.useFakeTimers();
    const writeText = vi.fn(() => Promise.resolve());
    mockClipboard(writeText);
    render(<CorrectedReferencePanel corrected={CORRECTED} />);

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Copiar referencia corregida" }));
    });

    expect(writeText).toHaveBeenCalledWith(CORRECTED.text);
    expect(screen.getByRole("button", { name: "Copiada" })).toBeTruthy();

    act(() => {
      vi.advanceTimersByTime(COPIED_MS);
    });
    expect(screen.getByRole("button", { name: "Copiar referencia corregida" })).toBeTruthy();
  });

  it("si el navegador no permite copiar, lo explica", async () => {
    mockClipboard(() => Promise.reject(new Error("sin permiso")));
    render(<CorrectedReferencePanel corrected={CORRECTED} />);

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Copiar referencia corregida" }));
    });

    expect(screen.getByRole("alert").textContent).toContain("No se pudo copiar");
  });
});
