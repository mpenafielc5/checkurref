import { describe, expect, it } from "vitest";
import { batchCsvFileName, buildBatchCsv } from "./batch-csv";
import type { BatchExport, ExportWork } from "./types";

const WORK: ExportWork = {
  fileName: "Ensayo.pdf",
  authors: ["Ana Ñauta", "Luis Peña"],
  status: "completado",
  errorMessage: null,
  references: [
    {
      order: 1,
      text: "Torres, A. (2020). Título.",
      verdict: "discrepancia",
      differentFields: ["anio", "contenedor"],
    },
    { order: 2, text: "Vera, B. (2021). Otro.", verdict: "verificada", differentFields: [] },
  ],
};

function csvOf(...works: ExportWork[]): string {
  const batch: BatchExport = { name: "Lote", works };
  return buildBatchCsv(batch);
}

function linesOf(csv: string): string[] {
  return csv.replace("﻿", "").split("\r\n").filter(Boolean);
}

describe("buildBatchCsv", () => {
  it("empieza con la marca UTF-8 para que Excel respete las tildes y la ñ", () => {
    expect(csvOf(WORK).charCodeAt(0)).toBe(0xfeff);
    expect(csvOf(WORK)).toContain("Ana Ñauta, Luis Peña");
  });

  it("tiene una fila por referencia con autores, archivo, veredicto y campos", () => {
    const lines = linesOf(csvOf(WORK));

    expect(lines).toEqual([
      "Autores;Archivo;N.º;Referencia;Veredicto;Campos con diferencias",
      "Ana Ñauta, Luis Peña;Ensayo.pdf;1;Torres, A. (2020). Título.;Con discrepancias;Año, Revista o libro",
      "Ana Ñauta, Luis Peña;Ensayo.pdf;2;Vera, B. (2021). Otro.;Verificada;",
    ]);
  });

  it("identifica por el aviso el trabajo con portada no reconocida", () => {
    expect(linesOf(csvOf({ ...WORK, authors: [] }))[1]).toMatch(/^Portada no reconocida;Ensayo/);
  });

  it("una referencia sin veredicto lo dice", () => {
    const references = [{ ...WORK.references[1], verdict: null }];

    expect(linesOf(csvOf({ ...WORK, references }))[1]).toContain(
      "Sin veredicto: una fuente no respondió",
    );
  });

  it("el trabajo sin referencias no desaparece: indica su estado o su error", () => {
    const lines = linesOf(
      csvOf(
        { ...WORK, status: "verificando", references: [] },
        { ...WORK, status: "error", errorMessage: "PDF dañado.", references: [] },
        { ...WORK, references: [] },
      ),
    );

    expect(lines[1]).toContain(";En análisis;");
    expect(lines[2]).toContain(";Error: PDF dañado.;");
    expect(lines[3]).toContain(";Sin referencias;");
  });

  it("protege el separador, las comillas y los saltos de línea del texto", () => {
    const references = [
      { order: 1, text: 'Uno; "dos"\ny tres', verdict: "verificada", differentFields: [] },
    ];

    expect(linesOf(csvOf({ ...WORK, references }))[1]).toContain('"Uno; ""dos"" y tres"');
  });

  it("una celda que Excel tomaría como fórmula queda como texto", () => {
    const authors = ['=HYPERLINK("http://x")'];
    const line = linesOf(csvOf({ ...WORK, authors, fileName: "@archivo.pdf" }))[1];

    expect(line.startsWith(`"'=HYPERLINK(""http://x"")"`)).toBe(true);
    expect(line).toContain(";'@archivo.pdf;");
  });
});

describe("batchCsvFileName", () => {
  it("quita tildes y signos del nombre del lote", () => {
    expect(batchCsvFileName("Metodología 5B · Ensayo")).toBe(
      "resultados-metodologia-5b-ensayo.csv",
    );
  });

  it("un nombre sin letras ni números no deja el archivo sin nombre", () => {
    expect(batchCsvFileName("···")).toBe("resultados-lote.csv");
  });
});
