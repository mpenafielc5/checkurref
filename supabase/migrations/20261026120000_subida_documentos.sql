-- CheckUrRef · Migración 3: subida de documentos (HU-04).
--
-- 1. Cada archivo es un trabajo independiente: se elimina documentos.version
--    (observación de la Asesoría 1). Dos archivos con el mismo nombre son dos
--    trabajos distintos.
-- 2. Índice para encontrar rápido un PDF idéntico del mismo usuario (sha256) y
--    no volver a analizarlo.
-- 3. Lectura: cada usuario ve sus documentos, sus análisis y sus PDF. La
--    escritura la hace solo el backend con la clave de servicio.
--
-- Nadie elige la norma al subir: el pipeline la detecta (APA, IEEE o MIXTA) y
-- la guarda en analisis.norma_detectada, que ya existe.

-- ---------------------------------------------------------------------------
-- Sin versiones
-- ---------------------------------------------------------------------------
alter table public.documentos drop column version;

comment on table public.documentos is
  'Cada PDF subido. Cada archivo es un trabajo independiente, aunque el nombre coincida.';

-- ---------------------------------------------------------------------------
-- PDF idéntico del mismo usuario
-- ---------------------------------------------------------------------------
create index on public.documentos (propietario_id, sha256);

-- ---------------------------------------------------------------------------
-- Lectura de lo propio (los lotes del docente llegan con HU-08)
-- ---------------------------------------------------------------------------
grant select on public.documentos to authenticated;
grant select on public.analisis to authenticated;

create policy "documentos: cada usuario ve los suyos"
  on public.documentos for select
  to authenticated
  using (propietario_id = (select auth.uid()));

create policy "analisis: cada usuario ve los de sus documentos"
  on public.analisis for select
  to authenticated
  using (
    exists (
      select 1
      from public.documentos d
      where d.id = documento_id
        and d.propietario_id = (select auth.uid())
    )
  );

-- Los PDF se guardan en documentos/<id del usuario>/<id del documento>.pdf
create policy "pdf: cada usuario lee los suyos"
  on storage.objects for select
  to authenticated
  using (
    bucket_id = 'documentos'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );
