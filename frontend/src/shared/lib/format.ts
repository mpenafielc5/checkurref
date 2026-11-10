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

/**
 * Parte de un total, por ejemplo las referencias con un veredicto. Lo que apenas
 * existe no se redondea a 0 % ni a 100 %: daría a entender que no hay ninguna o
 * que son todas.
 */
export function shareLabel(count: number, total: number): string {
  if (total === 0) return "—";
  const percent = (count / total) * 100;
  if (count > 0 && percent < 1) return "< 1 %";
  if (count < total && percent > 99) return "> 99 %";
  return formatPercent(percent);
}

export function formatFileSize(bytes: number): string {
  const megabytes = bytes / (1024 * 1024);
  return `${formatDecimal(megabytes, 1)} MB`;
}
