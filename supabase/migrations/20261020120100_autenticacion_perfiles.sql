-- CheckUrRef · Migración 2: autenticación institucional y perfiles.
--
-- 1. Solo las cuentas @unemi.edu.ec pueden registrarse (validado en el servidor).
-- 2. Cada cuenta nueva recibe automáticamente un perfil con rol "estudiante".
-- 3. Cada usuario puede leer su propio perfil; el administrador puede leer todos.
-- 4. Bucket privado para los PDF (las políticas de acceso llegan con la subida, HU-04).

-- ---------------------------------------------------------------------------
-- Rol del usuario actual. SECURITY DEFINER evita la recursión de RLS al
-- consultar perfiles desde una política de la propia tabla perfiles.
-- ---------------------------------------------------------------------------
create or replace function public.rol_actual()
returns public.rol_usuario
language sql
stable
security definer
set search_path = ''
as $$
  select rol from public.perfiles where id = (select auth.uid());
$$;

revoke execute on function public.rol_actual() from public, anon;
grant execute on function public.rol_actual() to authenticated;

-- ---------------------------------------------------------------------------
-- Registro de usuarios: rechaza dominios externos y crea el perfil.
-- Si se lanza la excepción, Supabase cancela la creación de la cuenta.
-- ---------------------------------------------------------------------------
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

  insert into public.perfiles (id, nombre_completo, correo, rol)
  values (new.id, left(nombre, 120), left(correo_usuario, 160), 'estudiante');

  return new;
end;
$$;

revoke execute on function public.registrar_usuario_nuevo() from public, anon, authenticated;

create trigger al_crear_usuario
  after insert on auth.users
  for each row execute function public.registrar_usuario_nuevo();

-- ---------------------------------------------------------------------------
-- Permisos sobre perfiles. Las tablas nuevas no se exponen automáticamente,
-- así que cada permiso se otorga de forma explícita.
-- ---------------------------------------------------------------------------
grant select on public.perfiles to authenticated;
-- El usuario solo puede editar sus datos personales, nunca su rol ni su estado.
grant update (nombre_completo, carrera) on public.perfiles to authenticated;

create policy "perfiles: cada usuario ve su perfil"
  on public.perfiles for select
  to authenticated
  using (id = (select auth.uid()));

create policy "perfiles: el administrador ve todos los perfiles"
  on public.perfiles for select
  to authenticated
  using ((select public.rol_actual()) = 'admin');

create policy "perfiles: cada usuario edita sus datos"
  on public.perfiles for update
  to authenticated
  using (id = (select auth.uid()))
  with check (id = (select auth.uid()));

-- El backend usa la clave de servicio (service_role), que ignora RLS pero
-- necesita permisos sobre las tablas porque no se exponen automáticamente.
grant select, insert, update, delete on all tables in schema public to service_role;
grant execute on function public.rol_actual() to service_role;

-- ---------------------------------------------------------------------------
-- Almacenamiento privado de los PDF (máximo 10 MB, solo application/pdf).
-- ---------------------------------------------------------------------------
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('documentos', 'documentos', false, 10485760, array['application/pdf'])
on conflict (id) do nothing;
