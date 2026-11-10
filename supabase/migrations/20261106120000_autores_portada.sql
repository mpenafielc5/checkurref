-- CheckUrRef · Migración 6: autores leídos de la portada del PDF (T23, RF19).
--
-- En un lote, muchos trabajos llegan con el mismo nombre de archivo: el docente los
-- distingue por sus autores. Solo agrega una columna, con valor por omisión, así que
-- el código que aún no la conoce sigue funcionando.

alter table public.t_documentos
  add column autores jsonb not null default '[]'::jsonb;

comment on column public.t_documentos.autores is
  'Autores leídos de la portada, uno por elemento. Lista vacía: portada no reconocida.';

notify pgrst, 'reload schema';
