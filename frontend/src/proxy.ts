import { NextResponse, type NextRequest } from "next/server";
import { redirectWithSession, updateSession } from "@/shared/lib/supabase/proxy";

/** Rutas que requieren sesión iniciada. */
const PROTECTED_PREFIXES = ["/estudiante", "/docente", "/admin", "/ayuda", "/inicio"];

function isProtected(pathname: string): boolean {
  return PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

export async function proxy(request: NextRequest) {
  const { response, userId } = await updateSession(request);
  const { pathname } = request.nextUrl;

  if (!userId && isProtected(pathname)) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (userId && pathname === "/login") {
    return redirectWithSession(response, new URL("/inicio", request.url));
  }

  return response;
}

export const config = {
  // Excluye archivos estáticos e imágenes para no frenar su carga.
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
