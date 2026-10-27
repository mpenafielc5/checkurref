/*
 * Informe de ejemplo de la maqueta 12. Se reemplaza por el informe real de la
 * API en HU-06. Tiene 34 referencias para mostrar la paginación de 10 en 10.
 */
import type { Verdict } from "@/shared/lib/verdicts";
import type { FormatFinding, ReferenceResult, ReferenceSegment, Report } from "./types";

type SampleSource = {
  authors: string;
  shortAuthors: string;
  year: string;
  title: string;
  container: string;
  tail: string;
};

const SOURCES: SampleSource[] = [
  {
    authors: "Rivas, A.",
    shortAuthors: "Rivas",
    year: "2020",
    title: "Evaluación formativa en entornos virtuales",
    container: "Revista Educación Digital",
    tail: ", 8(1), 10–22.",
  },
  {
    authors: "Torres, A. y Vera, C.",
    shortAuthors: "Torres, Vera",
    year: "2019",
    title: "Metodologías ágiles en proyectos universitarios",
    container: "Revista de Ingeniería de Software",
    tail: ", 11(3), 101–117.",
  },
  {
    authors: "Mendoza, L.",
    shortAuthors: "Mendoza",
    year: "2022",
    title: "Calidad de datos en sistemas de información académicos",
    container: "Ciencia y Sociedad",
    tail: ", 47(2), 33–49.",
  },
  {
    authors: "Ruiz, C., Ñauta, P. y Salas, D.",
    shortAuthors: "Ruiz, Ñauta, Salas",
    year: "2021",
    title: "Lectura crítica de fuentes en la educación superior",
    container: "Revista Iberoamericana de Educación",
    tail: ", 85(1), 59–76.",
  },
  {
    authors: "Castro, J.",
    shortAuthors: "Castro",
    year: "2023",
    title: "Aprendizaje automático aplicado a la deserción estudiantil",
    container: "Revista Tecnológica ESPOL",
    tail: ", 35(1), 1–15.",
  },
];

function segmentsOf(source: SampleSource): ReferenceSegment[] {
  return [
    { text: source.authors, field: "authors" },
    { text: " " },
    { text: `(${source.year})`, field: "year" },
    { text: ". " },
    { text: source.title, field: "title" },
    { text: ". " },
    { text: source.container, field: "container" },
    { text: source.tail },
  ];
}

/** Hallazgo de ejemplo: la obra tiene DOI en Crossref, pero la referencia no lo incluye. */
function missingDoi(source: SampleSource, order: number): FormatFinding {
  return {
    message: "Falta el DOI. La obra lo tiene registrado y APA 7 pide incluirlo al final.",
    given: `…${source.tail}`,
    expected: `…${source.tail} https://doi.org/10.0000/ejemplo.${order}`,
  };
}

function sampleReference(order: number, verdict: Verdict): ReferenceResult {
  const source = SOURCES[order % SOURCES.length];
  const base = {
    order,
    verdict,
    page: 12 + Math.floor((order - 1) / 9),
    formatFindings: order % 6 === 0 ? [missingDoi(source, order)] : [],
    segments: segmentsOf(source),
  };
  const sameTitle = {
    label: "Título",
    given: source.title,
    official: source.title,
    matches: true,
  };
  const sameAuthors = {
    label: "Autores",
    given: source.shortAuthors,
    official: source.shortAuthors,
    matches: true,
  };

  switch (verdict) {
    case "verificada":
      return {
        ...base,
        comparisons: [
          { label: "Año", given: source.year, official: source.year, matches: true },
          sameTitle,
          sameAuthors,
        ],
        nli: { field: "título", entailment: 96, neutral: 3, contradiction: 1 },
      };
    case "discrepancia":
      return {
        ...base,
        comparisons: [
          {
            label: "Año",
            given: source.year,
            official: String(Number(source.year) - 2),
            matches: false,
          },
          sameTitle,
          sameAuthors,
        ],
        nli: { field: "título", entailment: 91, neutral: 7, contradiction: 2 },
      };
    case "contradiccion":
      return {
        ...base,
        comparisons: [
          { label: "DOI", given: "10.5281/zenodo.0000", official: "No existe", matches: false },
          {
            label: "Título",
            given: source.title,
            official: "Gestión del talento humano en pequeñas empresas familiares",
            matches: false,
          },
        ],
        nli: { field: "título", entailment: 4, neutral: 12, contradiction: 84 },
      };
    case "sin_respaldo":
    case "no_verificable":
      return { ...base, comparisons: [], nli: null };
  }
}

/** Veredicto de cada referencia que no es "verificada", por su número. */
const FINDINGS: Record<number, Verdict> = {
  3: "discrepancia",
  5: "no_verificable",
  7: "discrepancia",
  10: "sin_respaldo",
  15: "discrepancia",
  18: "contradiccion",
  22: "discrepancia",
  26: "sin_respaldo",
  29: "discrepancia",
  31: "no_verificable",
};

const REFERENCES = Array.from({ length: 34 }, (_, index) =>
  sampleReference(index + 1, FINDINGS[index + 1] ?? "verificada"),
);

/** Cantidad de referencias por veredicto, calculada de la misma lista. */
function countVerdicts(references: ReferenceResult[]): Record<Verdict, number> {
  const counts: Record<Verdict, number> = {
    verificada: 0,
    discrepancia: 0,
    contradiccion: 0,
    sin_respaldo: 0,
    no_verificable: 0,
  };
  for (const reference of references) counts[reference.verdict] += 1;
  return counts;
}

export const SAMPLE_REPORT: Report = {
  analysisId: "a7f3",
  fileName: "Avance_cap2.pdf",
  standard: "APA",
  index: 82,
  counts: countVerdicts(REFERENCES),
  references: REFERENCES,
};
