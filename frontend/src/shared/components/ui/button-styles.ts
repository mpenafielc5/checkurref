/*
 * Estilos de botón de las maquetas: forma de píldora.
 * - primary: tinta oscura, para la acción principal de cada pantalla.
 * - secondary: fondo claro con borde, para acciones alternativas.
 * Se aplican tanto a <button> como a <Link>.
 * Cursor: un botón desactivado muestra "no permitido"; uno que está
 * procesando (aria-busy) muestra "espera".
 */

type ButtonVariant = "primary" | "secondary";

type ButtonStyleOptions = {
  variant?: ButtonVariant;
  fullWidth?: boolean;
};

const BASE =
  "inline-flex h-control items-center justify-center gap-2 rounded-pill px-5 text-small font-semibold transition-colors disabled:opacity-70 disabled:not-aria-busy:cursor-not-allowed aria-busy:cursor-wait";

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-action text-on-action hover:bg-action-hover",
  secondary: "border border-hairline-strong bg-surface text-ink hover:border-ink",
};

export function buttonStyles({ variant = "primary", fullWidth = false }: ButtonStyleOptions = {}) {
  return [BASE, VARIANTS[variant], fullWidth ? "w-full" : ""].filter(Boolean).join(" ");
}
