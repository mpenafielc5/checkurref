import { NextResponse, type NextRequest } from "next/server";
import { errorCodeFromOAuthFailure, isInstitutionalEmail } from "@/features/auth/rules";
import { createSupabaseServerClient } from "@/shared/lib/supabase/server";

/**
 * Google y Supabase regresan aquí después del inicio de sesión.
 * Se canjea el código por una sesión y se vuelve a comprobar el dominio,
 * además de la validación que ya hace la base de datos.
 */
export async function GET(request: NextRequest) {
  const { searchParams, origin } = request.nextUrl;
  const loginWithError = (code: string) =>
    NextResponse.redirect(new URL(`/login?error=${code}`, origin));

  const code = searchParams.get("code");
  if (!code) {
    return loginWithError(errorCodeFromOAuthFailure(searchParams.get("error_description")));
  }

  const supabase = await createSupabaseServerClient();
  const { data, error } = await supabase.auth.exchangeCodeForSession(code);

  if (error || !data.user) {
    return loginWithError("oauth");
  }

  if (!isInstitutionalEmail(data.user.email)) {
    await supabase.auth.signOut();
    return loginWithError("dominio");
  }

  return NextResponse.redirect(new URL("/inicio", origin));
}
