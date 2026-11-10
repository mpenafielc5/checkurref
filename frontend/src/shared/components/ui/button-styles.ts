/*
 * Estilos de botón de las maquetas: forma de píldora.
 * - primary: tinta oscura, para la acción principal de cada pantalla.
 * - secondary: fondo claro con borde, para acciones alternativas.
 * - danger: relleno rojo, para confirmar una acción destructiva.
 * - dangerQuiet: igual a secondary en reposo y rojo al pasar el cursor, para ofrecerla sin que domine la pantalla.
 * - restore: relleno verde, para confirmar que se restablece algo.
 * - restoreQuiet: igual a secondary en reposo y verde al pasar el cursor, para ofrecer esa acción.
 * Se aplican tanto a <button> como a <Link>.
 * Cursor: un botón desactivado muestra "no permitido"; uno que está
 * procesando (aria-busy) muestra "espera".
 */

type ButtonVariant =
  "primary" | "secondary" | "danger" | "dangerQuiet" | "restore" | "restoreQuiet";

type ButtonStyleOptions = {
  variant?: ButtonVariant;
  fullWidth?: boolean;
};

const BASE =
  "inline-flex h-control touch-manipulation items-center justify-center gap-2 rounded-pill px-5 text-small font-semibold transition-colors disabled:opacity-70 disabled:not-aria-busy:cursor-not-allowed aria-busy:cursor-wait";

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-action text-on-action hover:bg-action-hover",
  secondary: "border border-hairline-strong bg-surface text-ink hover:border-ink",
  danger: "bg-danger text-on-danger hover:bg-danger-hover",
  dangerQuiet:
    "border border-hairline-strong bg-surface text-ink hover:border-danger hover:bg-danger hover:text-on-danger",
  restore: "bg-restore text-on-restore hover:bg-restore-hover",
  restoreQuiet:
    "border border-hairline-strong bg-surface text-ink hover:border-restore hover:bg-restore hover:text-on-restore",
};

export function buttonStyles({ variant = "primary", fullWidth = false }: ButtonStyleOptions = {}) {
  return [BASE, VARIANTS[variant], fullWidth ? "w-full" : ""].filter(Boolean).join(" ");
}
