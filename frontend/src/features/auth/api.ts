import { connection } from "next/server";
import { cache } from "react";
import { createSupabaseServerClient } from "@/shared/lib/supabase/server";
import { safeAvatarUrl } from "./rules";
import type { Profile } from "./types";

/**
 * Perfil del usuario con sesión activa, o null si no hay sesión.
 * cache() evita consultar la base de datos dos veces en la misma petición
 * (por ejemplo, la barra superior y la verificación del rol).
 */
export const getCurrentProfile = cache(async (): Promise<Profile | null> => {
  // La sesión depende de cada visita: Supabase consulta la hora actual para
  // revisar si el token venció, así que esta parte no se prerenderiza.
  await connection();

  const supabase = await createSupabaseServerClient();

  const { data: claimsData } = await supabase.auth.getClaims();
  const claims = claimsData?.claims;
  const userId = claims?.sub;
  if (!userId) return null;

  const { data, error } = await supabase
    .from("perfiles")
    .select("id, nombre_completo, correo, rol, carrera, activo")
    .eq("id", userId)
    .single();

  if (error || !data) return null;

  return {
    id: data.id,
    fullName: data.nombre_completo,
    email: data.correo,
    role: data.rol,
    career: data.carrera,
    active: data.activo,
    // Google envía la foto en los datos de la sesión; no se guarda en la base.
    avatarUrl: safeAvatarUrl(claims.user_metadata?.avatar_url ?? claims.user_metadata?.picture),
  };
});
