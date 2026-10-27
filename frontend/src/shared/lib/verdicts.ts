/*
 * Los cinco veredictos, iguales en todo el sistema: mismo nombre, color y
 * descripción. Los valores coinciden con el tipo ENUM "veredicto" de la base.
 */

export type Verdict =
  "verificada" | "discrepancia" | "contradiccion" | "sin_respaldo" | "no_verificable";

type VerdictInfo = {
  label: string;
  description: string;
  /** Etiqueta en forma de píldora: fondo suave y texto oscuro del mismo tono. */
  badgeClass: string;
  /** Marca de color para leyendas y barras. */
  swatchClass: string;
};

export const VERDICTS: Record<Verdict, VerdictInfo> = {
  verificada: {
    label: "Verificada",
    description: "Coincide con el registro de Crossref u OpenAlex.",
    badgeClass: "bg-verdict-verified-soft text-verdict-verified-text",
    swatchClass: "bg-verdict-verified",
  },
  discrepancia: {
    label: "Con discrepancias",
    description: "La obra existe, pero hay campos alterados: año, autores o título incompleto.",
    badgeClass: "bg-verdict-discrepancy-soft text-verdict-discrepancy-text",
    swatchClass: "bg-verdict-discrepancy",
  },
  contradiccion: {
    label: "Contradicción",
    description: "El DOI no existe o los datos contradicen el registro.",
    badgeClass: "bg-verdict-contradiction-soft text-verdict-contradiction-text",
    swatchClass: "bg-verdict-contradiction",
  },
  sin_respaldo: {
    label: "Sin respaldo",
    description: "No se encontró ninguna obra candidata: posible referencia fabricada.",
    badgeClass: "bg-verdict-unsupported-soft text-verdict-unsupported-text",
    swatchClass: "bg-verdict-unsupported",
  },
  no_verificable: {
    label: "No verificable",
    description:
      "Crossref y OpenAlex no registran este tipo de obra, así que no se pudo comprobar.",
    badgeClass: "bg-verdict-unverifiable-soft text-verdict-unverifiable-text",
    swatchClass: "bg-verdict-unverifiable",
  },
};

export const VERDICT_ORDER: Verdict[] = [
  "verificada",
  "discrepancia",
  "contradiccion",
  "sin_respaldo",
  "no_verificable",
];
