/*
 * Tipos de las tablas de Supabase que usa el frontend.
 * Se amplían a medida que cada módulo empieza a leer nuevas tablas.
 */

export type UserRole = "estudiante" | "docente" | "admin";

export type Database = {
  public: {
    Tables: {
      perfiles: {
        Row: {
          id: string;
          nombre_completo: string;
          correo: string;
          rol: UserRole;
          carrera: string | null;
          activo: boolean;
          creado_en: string;
        };
        Insert: never;
        Update: {
          nombre_completo?: string;
          carrera?: string | null;
        };
        Relationships: [];
      };
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
    Enums: {
      rol_usuario: UserRole;
    };
    CompositeTypes: Record<string, never>;
  };
};
