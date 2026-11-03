import { describe, expect, it } from "vitest";
import { isReportDto, toReport, type ReportDto } from "./report-mapper";

const REFERENCE: ReportDto["references"][number] = {
  order: 1,
  page: 12,
  norm: "APA",
  text: "Pérez, M. (2019). Redes. Revista Andina, 8(1), 10-25.",
  segments: [
    { text: "Pérez, M.", field: "autores" },
    { text: " (", field: null },
    { text: "2019", field: "anio" },
    { text: "). ", field: null },
  ],
  verdict: "discrepancia",
  comparisons: [
    { field: "titulo", given: "Redes", official: "Redes", matches: true },
    { field: "anio", given: "2019", official: "2021", matches: false },
    { field: "doi", given: "10.1000/x", official: null, matches: false },
  ],
  nli: [
    { field: "autores", entailment: 0.06, neutral: 0.04, contradiction: 0.9 },
    { field: "titulo", entailment: 0.962, neutral: 0.03, contradiction: 0.008 },
  ],
  veracity_findings: [
    {
      code: "ANIO_DISTINTO",
      severity: "advertencia",
      message: "El año no coincide.",
      field: "anio",
      given: "2019",
      official: "2021",
    },
  ],
  format_findings: [
    {
      code: "APA_DOI_FALTA",
      severity: "advertencia",
      message: "Falta el DOI.",
      field: "doi",
      given: "…10-25.",
      official: "…10-25. https://doi.org/10.1234/x",
    },
  ],
  corrected: {
    text: "Pérez, M. (2021). Redes.",
    segments: [
      { text: "Pérez, M. (", italic: false, changed: false },
      { text: "2021", italic: false, changed: true },
      { text: "). Redes.", italic: false, changed: false },
    ],
  },
};

const DTO: ReportDto = {
  analysis_id: "a7f3",
  file_name: "Avance_cap2.pdf",
  norm: "MIXTA",
  index: 88.89,
  counts: {
    verificada: 8,
    discrepancia: 1,
    contradiccion: 0,
    sin_respaldo: 0,
    no_verificable: 0,
    error_consulta: 1,
  },
  references: [REFERENCE],
};

describe("toReport", () => {
  it("traduce el resumen del informe", () => {
    const report = toReport(DTO);

    expect(report.fileName).toBe("Avance_cap2.pdf");
    expect(report.standard).toBe("APA e IEEE");
    expect(report.index).toBe(89);
    expect(report.counts.verificada).toBe(8);
    expect(report.queryErrors).toBe(1);
  });

  it("pone los nombres visibles de los campos y marca lo que no está registrado", () => {
    const [reference] = toReport(DTO).references;

    expect(reference.comparisons.map((row) => row.label)).toEqual(["Título", "Año", "DOI"]);
    expect(reference.comparisons[2].official).toBe("No registrado");
  });

  it("colorea los campos del texto original", () => {
    const [reference] = toReport(DTO).references;

    expect(reference.segments.map((segment) => segment.field)).toEqual([
      "authors",
      undefined,
      "year",
      undefined,
    ]);
  });

  it("muestra el NLI del título en porcentaje", () => {
    const [reference] = toReport(DTO).references;

    expect(reference.nli).toEqual({
      field: "título",
      entailment: 96,
      neutral: 3,
      contradiction: 1,
    });
  });

  it("separa el hallazgo de formato y trae la referencia corregida", () => {
    const [reference] = toReport(DTO).references;

    expect(reference.formatFindings).toEqual([
      { message: "Falta el DOI.", given: "…10-25.", expected: "…10-25. https://doi.org/10.1234/x" },
    ]);
    expect(reference.corrected?.text).toBe("Pérez, M. (2021). Redes.");
    expect(reference.notice).toBeNull();
  });

  it("una referencia sin veredicto lleva el motivo como aviso", () => {
    const report = toReport({
      ...DTO,
      references: [
        {
          ...REFERENCE,
          verdict: null,
          comparisons: [],
          nli: [],
          corrected: null,
          format_findings: [],
          veracity_findings: [
            {
              code: "ERROR_CONSULTA",
              severity: "info",
              message: "No se pudo consultar Crossref ni OpenAlex.",
              field: null,
              given: null,
              official: null,
            },
          ],
        },
      ],
    });

    const [reference] = report.references;
    expect(reference.verdict).toBeNull();
    expect(reference.nli).toBeNull();
    expect(reference.notice).toBe("No se pudo consultar Crossref ni OpenAlex.");
  });

  it("sin norma detectada y sin índice", () => {
    const report = toReport({ ...DTO, norm: null, index: null });

    expect(report.standard).toBe("Norma no identificada");
    expect(report.index).toBeNull();
  });
});

describe("isReportDto", () => {
  it("reconoce la respuesta del informe y rechaza otra cosa", () => {
    expect(isReportDto(DTO)).toBe(true);
    expect(isReportDto({ detail: "No se encontró el análisis." })).toBe(false);
    expect(isReportDto(null)).toBe(false);
  });
});
