import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SAMPLE_REPORT } from "../sample-data";
import { PrintButton } from "./print-button";
import { PrintableReport } from "./printable-report";

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

function printedReferences(): HTMLElement[] {
  const list = screen.getByRole("list", { name: "Referencias", hidden: true });
  return within(list)
    .getAllByRole("listitem", { hidden: true })
    .filter((item) => item.parentElement === list);
}

describe("PrintableReport", () => {
  it("al imprimir, el PDF toma el nombre del trabajo y luego vuelve el título", () => {
    document.title = "CheckUrRef";
    render(<PrintableReport report={SAMPLE_REPORT} />);

    fireEvent(window, new Event("beforeprint"));
    const printing = document.title;
    fireEvent(window, new Event("afterprint"));

    expect(printing).toBe(`Informe CheckUrRef - ${SAMPLE_REPORT.fileName.replace(/\.pdf$/i, "")}`);
    expect(document.title).toBe("CheckUrRef");
  });

  it("trae todas las referencias, sin filtro ni páginas", () => {
    render(<PrintableReport report={SAMPLE_REPORT} />);

    expect(printedReferences()).toHaveLength(SAMPLE_REPORT.references.length);
  });

  it("escribe el nombre de cada veredicto para leerlo sin color", () => {
    render(<PrintableReport report={SAMPLE_REPORT} />);
    const [first, , third] = printedReferences();

    expect(first.textContent).toContain("[1] Verificada");
    expect(third.textContent).toContain("[3] Con discrepancias");
    expect(third.textContent).toContain("en la referencia;");
  });

  it("muestra la fecha del análisis y la de generación", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-11-14T20:05:00Z"));

    render(<PrintableReport report={SAMPLE_REPORT} />);

    expect(screen.getByText("12/11/2026, 10:30", { exact: false })).toBeTruthy();
    expect(screen.getByText("14/11/2026, 15:05", { exact: false })).toBeTruthy();
  });

  it("actualiza la fecha de generación justo antes de imprimir", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-11-14T20:05:00Z"));
    render(<PrintableReport report={SAMPLE_REPORT} />);

    vi.setSystemTime(new Date("2026-11-14T21:40:00Z"));
    fireEvent(window, new Event("beforeprint"));

    expect(screen.getByText("14/11/2026, 16:40", { exact: false })).toBeTruthy();
  });
});

describe("PrintButton", () => {
  it("abre el diálogo de impresión", () => {
    const print = vi.spyOn(window, "print").mockImplementation(() => undefined);
    render(<PrintButton />);

    fireEvent.click(screen.getByRole("button", { name: "Exportar PDF" }));

    expect(print).toHaveBeenCalledOnce();
  });
});
