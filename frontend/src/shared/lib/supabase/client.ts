import { createBrowserClient } from "@supabase/ssr";
import { getSupabaseEnv } from "@/shared/lib/env";
import type { Database } from "./database.types";

/** Cliente de Supabase para componentes que se ejecutan en el navegador. */
export function createSupabaseBrowserClient() {
  const { url, publishableKey } = getSupabaseEnv();
  return createBrowserClient<Database>(url, publishableKey);
}
