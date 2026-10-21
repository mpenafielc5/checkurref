import { NextResponse, type NextRequest } from "next/server";
import { createSupabaseServerClient } from "@/shared/lib/supabase/server";

/** Cierra la sesión y vuelve a la página pública. */
export async function POST(request: NextRequest) {
  const supabase = await createSupabaseServerClient();
  await supabase.auth.signOut();

  // 303: el navegador sigue la redirección con GET.
  return NextResponse.redirect(new URL("/", request.nextUrl.origin), { status: 303 });
}
