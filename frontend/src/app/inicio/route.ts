import { NextResponse, type NextRequest } from "next/server";
import { getCurrentProfile } from "@/features/auth/api";
import { homePathForRole } from "@/features/auth/rules";
import { createSupabaseServerClient } from "@/shared/lib/supabase/server";

/** Envía a cada usuario a la página de inicio de su rol. */
export async function GET(request: NextRequest) {
  const { origin } = request.nextUrl;
  const profile = await getCurrentProfile();

  if (!profile || !profile.active) {
    const supabase = await createSupabaseServerClient();
    await supabase.auth.signOut();
    const reason = profile ? "inactiva" : "oauth";
    return NextResponse.redirect(new URL(`/login?error=${reason}`, origin));
  }

  return NextResponse.redirect(new URL(homePathForRole(profile.role), origin));
}
