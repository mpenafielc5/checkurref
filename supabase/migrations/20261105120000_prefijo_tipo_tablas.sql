-- CheckUrRef · Migración 5: prefijo por tipo en el nombre de cada tabla.
--
-- Observación de la revisión del Sprint 2: el nombre de cada tabla indica su tipo.
--   m_  maestra: describe algo que existe por sí mismo (personas, obras, el
--       estándar de oro), cambia poco y la usan otras tablas.
--   t_  transaccional: cada fila nace de una operación (subir, analizar,
--       verificar, exportar o medir) y crece con el uso.
-- Los valores paramétricos (roles, estados, normas, veredictos y demás) son los
-- 10 tipos ENUM de la migración 1, por eso no hay tablas con prefijo p_.
--
-- Se conservan en minúsculas, sin comillas, como el resto del esquema.
-- RENAME no toca los datos: las llaves foráneas, los índices, los permisos, las
-- políticas RLS y la publicación de Realtime siguen a cada tabla. Solo hay que
-- volver a crear las dos funciones que nombran la tabla de perfiles en su texto.
--
-- Se aplica una sola vez en el SQL Editor, junto con el código que ya usa los
-- nombres nuevos: el backend y el frontend anteriores dejan de funcionar.

begin;

-- ---------------------------------------------------------------------------
-- Maestras
-- ---------------------------------------------------------------------------
alter table public.perfiles rename to m_perfiles;
alter table public.registros_crossref rename to m_registros_crossref;
alter table public.referencias_oro rename to m_referencias_oro;

-- ---------------------------------------------------------------------------
-- Transaccionales
-- ---------------------------------------------------------------------------
alter table public.lotes_auditoria rename to t_lotes_auditoria;
alter table public.documentos rename to t_documentos;
alter table public.analisis rename to t_analisis;
alter table public.reportes_exportados rename to t_reportes_exportados;
alter table public.referencias rename to t_referencias;
alter table public.extracciones rename to t_extracciones;
alter table public.hallazgos rename to t_hallazgos;
alter table public.verificaciones rename to t_verificaciones;
alter table public.inferencias_nli rename to t_inferencias_nli;
alter table public.corridas_benchmark rename to t_corridas_benchmark;

-- ---------------------------------------------------------------------------
-- Funciones que nombran la tabla en su texto (mismo cuerpo de la migración 2).
-- CREATE OR REPLACE conserva los permisos y el disparador al_crear_usuario.
-- ---------------------------------------------------------------------------
create or replace function public.rol_actual()
returns public.rol_usuario
language sql
stable
security definer
set search_path = ''
as $$
  select rol from public.m_perfiles where id = (select auth.uid());
$$;

create or replace function public.registrar_usuario_nuevo()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  correo_usuario text := lower(coalesce(new.email, ''));
  nombre text := coalesce(
    nullif(new.raw_user_meta_data ->> 'full_name', ''),
    nullif(new.raw_user_meta_data ->> 'name', ''),
    split_part(correo_usuario, '@', 1)
  );
begin
  if correo_usuario not like '%@unemi.edu.ec' then
    raise exception 'Solo se permiten cuentas institucionales @unemi.edu.ec';
  end if;

  insert into public.m_perfiles (id, nombre_completo, correo, rol)
  values (new.id, left(nombre, 120), left(correo_usuario, 160), 'estudiante');

  return new;
end;
$$;

commit;

-- La API de Supabase (PostgREST) vuelve a leer el esquema con los nombres nuevos.
notify pgrst, 'reload schema';
