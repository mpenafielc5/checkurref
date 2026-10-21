/** Formatos de números y fechas para la interfaz, en español de Ecuador. */

const LOCALE = "es-EC";

export function formatDecimal(value: number, fractionDigits = 2): string {
  return new Intl.NumberFormat(LOCALE, {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(value);
}

export function formatPercent(value: number): string {
  return `${Math.round(value)} %`;
}

export function formatFileSize(bytes: number): string {
  const megabytes = bytes / (1024 * 1024);
  return `${formatDecimal(megabytes, 1)} MB`;
}
