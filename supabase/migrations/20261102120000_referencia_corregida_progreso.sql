-- CheckUrRef · Migración 4: referencia corregida (HU-19) y progreso en vivo (HU-05).
--
-- 1. verificaciones.referencia_corregida: la referencia en APA 7 o IEEE armada
--    con los datos del registro de Crossref u OpenAlex al verificarla. Se guarda
--    al analizar, y no se calcula al abrir el informe, para que el informe sea
--    la evidencia de lo que se verificó ese día aunque la fuente cambie después,
--    y para que funcione también con obras de OpenAlex sin DOI (que no quedan en
--    registros_crossref).
-- 2. La tabla analisis entra en la publicación de Realtime: la pantalla de
--    progreso recibe cada cambio de estado y de avance sin consultar. Realtime
--    respeta RLS, así que cada usuario solo recibe sus propios análisis (la
--    política de lectura ya existe desde la migración 3).

-- ---------------------------------------------------------------------------
-- Referencia corregida
-- ---------------------------------------------------------------------------
alter table public.verificaciones add column referencia_corregida jsonb;

comment on column public.verificaciones.referencia_corregida is
  'Referencia corregida en segmentos [{texto, campo, cursiva, cambiado}]; el texto para '
  'copiar es la unión de los textos. Null si no es seguro que el registro sea la obra '
  'citada o si la norma no es APA ni IEEE.';

-- ---------------------------------------------------------------------------
-- Progreso en vivo
-- ---------------------------------------------------------------------------
do $$
begin
  if not exists (
    select 1
    from pg_publication_tables
    where pubname = 'supabase_realtime'
      and schemaname = 'public'
      and tablename = 'analisis'
  ) then
    alter publication supabase_realtime add table public.analisis;
  end if;
end
$$;
