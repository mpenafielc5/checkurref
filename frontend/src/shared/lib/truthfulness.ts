/*
 * Índice de veracidad: qué parte de las referencias que se pudieron comprobar
 * salió Verificada. El nivel (alto, medio o bajo) lo calcula el backend con los
 * cortes de RF20-CA02, los mismos del riesgo de un lote; aquí solo se muestra.
 */

import type { ChipTone } from "@/shared/components/ui/status-chip";
import type { Verdict } from "./verdicts";

export type IndexLevel = "alto" | "medio" | "bajo";

type IndexLevelInfo = {
  label: string;
  /** Qué hacer con ese resultado, en una frase. */
  advice: string;
  /** Color de la etiqueta (StatusChip). */
  tone: ChipTone;
  /** Trazo del anillo del informe. */
  strokeClass: string;
  /** El número solo, en una tabla. */
  textClass: string;
};

export const INDEX_LEVELS: Record<IndexLevel, IndexLevelInfo> = {
  alto: {
    label: "Índice alto",
    advice: "Casi todas las referencias coinciden con su registro.",
    tone: "success",
    strokeClass: "stroke-verdict-verified",
    textClass: "text-verdict-verified-text",
  },
  medio: {
    label: "Índice medio",
    advice: "Varias referencias necesitan revisión.",
    tone: "warning",
    strokeClass: "stroke-verdict-discrepancy",
    textClass: "text-verdict-discrepancy-text",
  },
  bajo: {
    label: "Índice bajo",
    advice: "Muchas referencias no coinciden con su registro y conviene revisarlas una por una.",
    tone: "danger",
    strokeClass: "stroke-verdict-contradiction",
    textClass: "text-verdict-contradiction-text",
  },
};

export const INDEX_LEVEL_ORDER: IndexLevel[] = ["alto", "medio", "bajo"];

/** Rango de cada nivel, como lo explica la Ayuda (RF20-CA02). */
export const INDEX_LEVEL_RANGES: Record<IndexLevel, string> = {
  alto: "De 85 a 100",
  medio: "De 60 a menos de 85",
  bajo: "Menos de 60",
};

/** El nivel que envía el backend; null si no viene o no es uno conocido. */
export function toIndexLevel(value: unknown): IndexLevel | null {
  return value === "alto" || value === "medio" || value === "bajo" ? value : null;
}

/**
 * Las referencias que cuentan en el índice: todas menos las No verificables
 * (RF12-CA04). Las que quedaron sin verificar por un error de consulta no
 * tienen veredicto y no llegan aquí.
 */
export function countedReferences(counts: Record<Verdict, number>): {
  verified: number;
  counted: number;
} {
  const counted =
    counts.verificada + counts.discrepancia + counts.contradiccion + counts.sin_respaldo;
  return { verified: counts.verificada, counted };
}

/** "17 de 20 referencias comprobadas están verificadas", en número correcto. */
export function indexExplanation(counts: Record<Verdict, number>): string {
  const { verified, counted } = countedReferences(counts);
  const noun = counted === 1 ? "referencia comprobada" : "referencias comprobadas";
  const verb = verified === 1 ? "está verificada" : "están verificadas";
  return `${verified} de ${counted} ${noun} ${verb}.`;
}
