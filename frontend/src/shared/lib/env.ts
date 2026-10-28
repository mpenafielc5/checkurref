/*
 * Variables de entorno públicas del frontend. Se leen con nombres literales
 * para que Next.js las incluya en el código del navegador, y solo cuando se
 * necesitan, para que importar este módulo nunca falle por sí solo.
 */

function required(name: string, value: string | undefined): string {
  if (!value) {
    throw new Error(`Falta la variable de entorno ${name}. Revisa frontend/.env.local.`);
  }
  return value;
}

/** Dirección de la API (FastAPI), sin barra final. */
export function getApiUrl(): string {
  return required("NEXT_PUBLIC_API_URL", process.env.NEXT_PUBLIC_API_URL).replace(/\/+$/, "");
}

export function getSupabaseEnv() {
  return {
    url: required("NEXT_PUBLIC_SUPABASE_URL", process.env.NEXT_PUBLIC_SUPABASE_URL),
    publishableKey: required(
      "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
      process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY,
    ),
  };
}
