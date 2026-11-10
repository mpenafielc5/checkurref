-- CheckUrRef · Migración 7: se quita la tabla de reportes exportados.
--
-- El diseño inicial generaba el PDF y el CSV en el servidor y registraba cada
-- exportación aquí. El aplicativo los genera en el navegador (HU-10 y HU-15), así
-- que ninguna parte del código lee ni escribe esta tabla y siempre estuvo vacía.
-- Con ella se va el tipo formato_reporte, que solo usaba su columna formato.

drop table if exists public.t_reportes_exportados;

drop type if exists public.formato_reporte;

notify pgrst, 'reload schema';
