/** Formatos de números y fechas para la interfaz, en español de Ecuador. */

const LOCALE = "es-EC";

export function formatDecimal(value: number, fractionDigits = 2): string {
  return new Intl.NumberFormat(LOCALE, {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(value);
}

/** Fecha corta como en las maquetas: 03/11/2026, en la hora de Ecuador. */
export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat(LOCALE, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "America/Guayaquil",
  }).format(new Date(iso));
}

/** Fecha y hora, para distinguir dos mediciones del mismo día. */
export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat(LOCALE, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "America/Guayaquil",
  }).format(new Date(iso));
}

export function formatPercent(value: number): string {
  return `${Math.round(value)} %`;
}

export function formatFileSize(bytes: number): string {
  const megabytes = bytes / (1024 * 1024);
  return `${formatDecimal(megabytes, 1)} MB`;
}
