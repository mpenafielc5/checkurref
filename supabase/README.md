# Base de datos (Supabase)

Las migraciones de `migrations/` son la única fuente del esquema. Se aplican en
orden por nombre (la fecha va al inicio).

| Migración | Contenido |
|---|---|
| `20261020120000_esquema_inicial.sql` | 13 tablas, 10 tipos ENUM, índices y RLS activado (modelo aprobado) |
| `20261020120100_autenticacion_perfiles.sql` | Registro solo @unemi.edu.ec, perfil automático, políticas de `perfiles`, bucket de PDF |
| `20261026120000_subida_documentos.sql` | Sin versiones (quita `documentos.version`), norma elegida en `analisis`, índice por sha256 y lectura de lo propio (HU-04) |
| `20261102120000_referencia_corregida_progreso.sql` | `verificaciones.referencia_corregida` (HU-19) y `analisis` en la publicación de Realtime para el progreso en vivo (HU-05) |
| `20261105120000_prefijo_tipo_tablas.sql` | Prefijo por tipo en cada tabla: `m_` maestras (`m_perfiles`, `m_registros_crossref`, `m_referencias_oro`) y `t_` transaccionales (las otras 10); los valores paramétricos son los ENUM |

## Cómo aplicarlas

1. Supabase → **SQL Editor** → **New query**.
2. Pegar el contenido de cada migración, **en orden**, y pulsar **Run**.
3. Una migración que ya se ejecutó **no se vuelve a ejecutar**: los cambios
   posteriores van en una migración nueva.

## Cambiar el rol de una cuenta

Mientras no exista la pantalla de usuarios (HU-11), el rol se cambia desde el
SQL Editor:

```sql
update public.m_perfiles set rol = 'admin' where correo = 'correo@unemi.edu.ec';
```

Valores posibles: `estudiante`, `docente`, `admin`.

## Desactivar una cuenta (nunca borrarla)

**No borrar usuarios desde el panel** (Authentication → Users → Delete). Las
tablas están enlazadas con `ON DELETE CASCADE`: borrar un usuario borra en
cadena su perfil, sus documentos, análisis, referencias y veredictos.

Para sacar a alguien del sistema se usa la desactivación lógica. La cuenta no
puede volver a ingresar (ve el aviso de cuenta desactivada) y sus datos se
conservan:

```sql
update public.m_perfiles set activo = false where correo = 'correo@unemi.edu.ec';
```

Para reactivarla, el mismo comando con `activo = true`. Cuando exista la
pantalla de usuarios (HU-11), el administrador lo hará desde ahí.
