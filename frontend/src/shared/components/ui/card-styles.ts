/*
 * Estilos de tarjeta de las maquetas: borde fino, esquinas redondeadas y sin sombra.
 * Se definen aquí una sola vez, como buttonStyles; cada pantalla conserva su
 * elemento (li, article, details…) y su disposición, y solo pide la tarjeta.
 * - size: card (radio de tarjeta) o panel (radio mayor, para bloques grandes).
 * - tone: fondo canvas (tarjeta sobre la superficie), surface (tarjeta sobre un
 *   fondo canvas) o none (lo pone la pantalla según su estado).
 * - strong: borde más marcado, para la tarjeta de cada referencia del informe.
 */

type CardSize = "card" | "panel";
type CardTone = "canvas" | "surface" | "none";

type CardStyleOptions = {
  size?: CardSize;
  tone?: CardTone;
  strong?: boolean;
};

const RADIUS: Record<CardSize, string> = {
  card: "rounded-card",
  panel: "rounded-panel",
};

const BACKGROUND: Record<CardTone, string> = {
  canvas: "bg-canvas",
  surface: "bg-surface",
  none: "",
};

export function cardStyles({
  size = "card",
  tone = "canvas",
  strong = false,
}: CardStyleOptions = {}): string {
  return [
    RADIUS[size],
    "border",
    strong ? "border-hairline-strong" : "border-hairline",
    BACKGROUND[tone],
  ]
    .filter(Boolean)
    .join(" ");
}
