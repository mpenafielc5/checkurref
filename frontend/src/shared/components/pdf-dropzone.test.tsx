import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PdfDropzone } from "./pdf-dropzone";

function choose(file: File) {
  const input = document.querySelector<HTMLInputElement>('input[type="file"]');
  if (!input) throw new Error("Falta el campo de archivo");
  fireEvent.change(input, { target: { files: [file] } });
}

const PDF = new File(["%PDF-1.7"], "S4TAREA1.pdf", { type: "application/pdf" });

describe("PdfDropzone de un solo archivo", () => {
  it("al elegir un PDF lo muestra en una ficha con la acción siguiente", () => {
    const onChange = vi.fn();
    render(
      <PdfDropzone title="Arrastra aquí" hint="máx. 10 MB" onChange={onChange}>
        <button type="button">Analizar referencias</button>
      </PdfDropzone>,
    );

    choose(PDF);

    expect(screen.getByText("S4TAREA1.pdf")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Analizar referencias" })).toBeTruthy();
    expect(onChange).toHaveBeenLastCalledWith([PDF]);
  });

  it("la ✕ quita el archivo y vuelve al estado inicial", () => {
    const onChange = vi.fn();
    render(<PdfDropzone title="Arrastra aquí" hint="máx. 10 MB" onChange={onChange} />);

    choose(PDF);
    fireEvent.click(screen.getByRole("button", { name: "Quitar S4TAREA1.pdf" }));

    expect(screen.queryByText("S4TAREA1.pdf")).toBeNull();
    expect(screen.getByText("Arrastra aquí")).toBeTruthy();
    expect(onChange).toHaveBeenLastCalledWith([]);
  });

  it("un archivo que no es PDF no se acepta y explica por qué", () => {
    const onChange = vi.fn();
    render(<PdfDropzone title="Arrastra aquí" hint="máx. 10 MB" onChange={onChange} />);

    choose(new File(["hola"], "notas.txt", { type: "text/plain" }));

    expect(screen.getByRole("alert").textContent).toBe("notas.txt: Solo se aceptan archivos PDF.");
    expect(onChange).toHaveBeenLastCalledWith([]);
  });
});

describe("PdfDropzone de varios archivos (lote)", () => {
  const OTRO = new File(["%PDF-1.7"], "Ensayo_B.pdf", { type: "application/pdf" });

  function chooseMany(files: File[]) {
    const input = document.querySelector<HTMLInputElement>('input[type="file"]');
    if (!input) throw new Error("Falta el campo de archivo");
    fireEvent.change(input, { target: { files } });
  }

  it("lista los archivos, marca los inválidos y solo envía los válidos", () => {
    const onChange = vi.fn();
    render(<PdfDropzone multiple title="Arrastra aquí" hint="hasta 40" onChange={onChange} />);

    chooseMany([PDF, new File(["hola"], "notas.txt", { type: "text/plain" })]);

    expect(screen.getByText("S4TAREA1.pdf")).toBeTruthy();
    expect(screen.getByText("Solo se aceptan archivos PDF.")).toBeTruthy();
    expect(onChange).toHaveBeenLastCalledWith([PDF]);
  });

  it("agregar más suma archivos sin repetir los que ya estaban", () => {
    const onChange = vi.fn();
    render(<PdfDropzone multiple title="Arrastra aquí" hint="hasta 40" onChange={onChange} />);

    chooseMany([PDF]);
    chooseMany([PDF, OTRO]);

    expect(onChange).toHaveBeenLastCalledWith([PDF, OTRO]);
  });

  it("la ✕ quita solo ese archivo del lote", () => {
    const onChange = vi.fn();
    render(<PdfDropzone multiple title="Arrastra aquí" hint="hasta 40" onChange={onChange} />);

    chooseMany([PDF, OTRO]);
    fireEvent.click(screen.getByRole("button", { name: "Quitar S4TAREA1.pdf" }));

    expect(screen.queryByText("S4TAREA1.pdf")).toBeNull();
    expect(screen.getByText("Ensayo_B.pdf")).toBeTruthy();
    expect(onChange).toHaveBeenLastCalledWith([OTRO]);
  });
});
