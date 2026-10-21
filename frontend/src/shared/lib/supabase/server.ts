import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { getSupabaseEnv } from "@/shared/lib/env";
import type { Database } from "./database.types";

/**
 * Cliente de Supabase para componentes de servidor y rutas.
 * Se crea uno por petición: la sesión viaja en las cookies del usuario.
 */
export async function createSupabaseServerClient() {
  const cookieStore = await cookies();
  const supabaseEnv = getSupabaseEnv();

  return createServerClient<Database>(supabaseEnv.url, supabaseEnv.publishableKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet) {
        try {
          cookiesToSet.forEach(({ name, value, options }) => cookieStore.set(name, value, options));
        } catch {
          // Los componentes de servidor no pueden escribir cookies; proxy.ts
          // se encarga de renovar la sesión en cada petición.
        }
      },
    },
  });
}
