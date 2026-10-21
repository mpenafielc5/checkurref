import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { getSupabaseEnv } from "@/shared/lib/env";
import type { Database } from "./database.types";

type SessionResult = {
  response: NextResponse;
  userId: string | null;
};

/**
 * Renueva la sesión de Supabase en cada petición y devuelve el usuario
 * verificado (la firma del token se valida con getClaims).
 */
export async function updateSession(request: NextRequest): Promise<SessionResult> {
  let response = NextResponse.next({ request });
  const supabaseEnv = getSupabaseEnv();

  const supabase = createServerClient<Database>(supabaseEnv.url, supabaseEnv.publishableKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet, headers) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options),
        );
        Object.entries(headers).forEach(([key, value]) => response.headers.set(key, value));
      },
    },
  });

  const { data } = await supabase.auth.getClaims();
  const userId = data?.claims.sub ?? null;

  return { response, userId };
}

/** Redirige conservando las cookies de sesión que se acaban de renovar. */
export function redirectWithSession(source: NextResponse, url: URL): NextResponse {
  const redirect = NextResponse.redirect(url);
  source.cookies.getAll().forEach((cookie) => redirect.cookies.set(cookie));
  return redirect;
}
