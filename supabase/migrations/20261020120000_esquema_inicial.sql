-- CheckUrRef · Migración 1: esquema inicial (13 tablas, 10 tipos ENUM).
-- Generado desde el modelo de datos aprobado (diagrama entidad-relación de la Semana 1).
-- gen_random_uuid() viene incluido en PostgreSQL 13+.

-- Tipos enumerados
CREATE TYPE rol_usuario AS ENUM ('estudiante', 'docente', 'admin');
CREATE TYPE estado_analisis AS ENUM ('en_cola', 'extrayendo', 'segmentando', 'verificando', 'completado', 'error');
CREATE TYPE norma_bibliografica AS ENUM ('APA', 'IEEE', 'MIXTA', 'DESCONOCIDA');
CREATE TYPE motor_extraccion AS ENUM ('anystyle', 'spacy');
CREATE TYPE estrategia_busqueda AS ENUM ('doi_directo', 'busqueda_bibliografica', 'sin_consulta');
CREATE TYPE veredicto AS ENUM ('verificada', 'discrepancia', 'contradiccion', 'sin_respaldo', 'no_verificable');
CREATE TYPE campo_nli AS ENUM ('titulo', 'autores', 'anio', 'contenedor');
CREATE TYPE tipo_hallazgo AS ENUM ('formato', 'veracidad');
CREATE TYPE severidad AS ENUM ('info', 'advertencia', 'critico');
CREATE TYPE formato_reporte AS ENUM ('pdf', 'csv');

-- Datos y rol de cada usuario. Extiende auth.users con la información propia del sistema.
CREATE TABLE perfiles (
  id UUID PRIMARY KEY,
  nombre_completo VARCHAR(120) NOT NULL,
  correo VARCHAR(160) NOT NULL UNIQUE,
  rol rol_usuario NOT NULL DEFAULT 'estudiante',
  carrera VARCHAR(120),
  activo BOOLEAN NOT NULL DEFAULT true,
  creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Grupo de trabajos que un docente audita en conjunto, por ejemplo un paralelo y una entrega.
CREATE TABLE lotes_auditoria (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  docente_id UUID NOT NULL REFERENCES perfiles(id) ON DELETE CASCADE,
  nombre VARCHAR(150) NOT NULL,
  descripcion TEXT,
  periodo_academico VARCHAR(20),
  creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Cada PDF subido. Si el estudiante sube una versión nueva, se crea otro documento con version + 1.
CREATE TABLE documentos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  propietario_id UUID NOT NULL REFERENCES perfiles(id) ON DELETE CASCADE,
  lote_id UUID REFERENCES lotes_auditoria(id) ON DELETE SET NULL,
  titulo VARCHAR(255) NOT NULL,
  nombre_archivo VARCHAR(255) NOT NULL,
  ruta_storage TEXT NOT NULL UNIQUE,
  sha256 CHAR(64) NOT NULL,
  tamano_bytes INTEGER NOT NULL CHECK (tamano_bytes <= 10485760),
  paginas SMALLINT,
  version SMALLINT NOT NULL DEFAULT 1,
  creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Una ejecución del pipeline sobre un documento. Un documento puede reanalizarse con otro modelo sin perder el historial.
CREATE TABLE analisis (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  documento_id UUID NOT NULL REFERENCES documentos(id) ON DELETE CASCADE,
  estado estado_analisis NOT NULL DEFAULT 'en_cola',
  progreso SMALLINT NOT NULL DEFAULT 0 CHECK (progreso BETWEEN 0 AND 100),
  total_referencias SMALLINT,
  norma_detectada norma_bibliografica,
  extractor_principal motor_extraccion NOT NULL DEFAULT 'anystyle',
  version_modelo VARCHAR(60) NOT NULL,
  indice_veracidad NUMERIC(5,2) CHECK (indice_veracidad BETWEEN 0 AND 100),
  mensaje_error TEXT,
  iniciado_en TIMESTAMPTZ,
  finalizado_en TIMESTAMPTZ,
  duracion_ms INTEGER,
  creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Registro de cada exportación de un informe, como evidencia de la revisión.
CREATE TABLE reportes_exportados (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analisis_id UUID NOT NULL REFERENCES analisis(id) ON DELETE CASCADE,
  generado_por UUID NOT NULL REFERENCES perfiles(id),
  formato formato_reporte NOT NULL,
  ruta_storage TEXT,
  creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Cada referencia detectada en la lista final del PDF, tal como aparece en el texto.
CREATE TABLE referencias (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analisis_id UUID NOT NULL REFERENCES analisis(id) ON DELETE CASCADE,
  orden SMALLINT NOT NULL,
  texto_crudo TEXT NOT NULL,
  pagina SMALLINT,
  norma norma_bibliografica,
  UNIQUE (analisis_id, orden)
);

-- Campos que separó cada motor. Con dos motores, cada referencia tiene hasta dos filas: base del Laboratorio AnyStyle vs spaCy.
CREATE TABLE extracciones (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  referencia_id UUID NOT NULL REFERENCES referencias(id) ON DELETE CASCADE,
  motor motor_extraccion NOT NULL,
  autores JSONB,
  anio SMALLINT,
  titulo TEXT,
  contenedor VARCHAR(255),
  editorial VARCHAR(255),
  volumen VARCHAR(20),
  numero VARCHAR(20),
  paginas VARCHAR(30),
  doi VARCHAR(255),
  tiempo_ms INTEGER,
  UNIQUE (referencia_id, motor)
);

-- Cada problema encontrado: de formato (norma APA o IEEE) o de veracidad (datos que no coinciden).
CREATE TABLE hallazgos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  referencia_id UUID NOT NULL REFERENCES referencias(id) ON DELETE CASCADE,
  tipo tipo_hallazgo NOT NULL,
  codigo VARCHAR(40) NOT NULL,
  severidad severidad NOT NULL,
  campo VARCHAR(30),
  valor_dado TEXT,
  valor_oficial TEXT,
  mensaje TEXT NOT NULL
);

-- Caché compartida de las obras consultadas en Crossref. Un DOI se consulta una sola vez.
CREATE TABLE registros_crossref (
  doi VARCHAR(255) PRIMARY KEY,
  titulo TEXT,
  autores JSONB,
  anio SMALLINT,
  contenedor VARCHAR(255),
  tipo VARCHAR(50),
  metadatos JSONB NOT NULL,
  consultado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Resultado de contrastar una referencia con la fuente oficial. Exactamente una por referencia.
CREATE TABLE verificaciones (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  referencia_id UUID NOT NULL UNIQUE REFERENCES referencias(id) ON DELETE CASCADE,
  crossref_doi VARCHAR(255) REFERENCES registros_crossref(doi),
  estrategia estrategia_busqueda NOT NULL,
  score_crossref NUMERIC(8,3),
  sim_titulo NUMERIC(4,3) CHECK (sim_titulo BETWEEN 0 AND 1),
  sim_autores NUMERIC(4,3) CHECK (sim_autores BETWEEN 0 AND 1),
  coincide_anio BOOLEAN,
  veredicto veredicto NOT NULL,
  indice_veracidad NUMERIC(5,2) CHECK (indice_veracidad BETWEEN 0 AND 100),
  verificado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Lo que respondió el modelo NLI para cada campo. Permite explicar cada veredicto.
CREATE TABLE inferencias_nli (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  verificacion_id UUID NOT NULL REFERENCES verificaciones(id) ON DELETE CASCADE,
  campo campo_nli NOT NULL,
  premisa TEXT NOT NULL,
  hipotesis TEXT NOT NULL,
  p_implicacion NUMERIC(5,4) NOT NULL CHECK (p_implicacion BETWEEN 0 AND 1),
  p_neutral NUMERIC(5,4) NOT NULL CHECK (p_neutral BETWEEN 0 AND 1),
  p_contradiccion NUMERIC(5,4) NOT NULL CHECK (p_contradiccion BETWEEN 0 AND 1),
  UNIQUE (verificacion_id, campo)
);

-- Conjunto de referencias anotadas a mano para medir la precisión de los extractores. No se relaciona con las demás tablas.
CREATE TABLE referencias_oro (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  texto TEXT NOT NULL,
  norma norma_bibliografica NOT NULL,
  campos_anotados JSONB NOT NULL,
  es_alterada BOOLEAN NOT NULL DEFAULT false,
  tipo_alteracion VARCHAR(40),
  creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Resultados de cada medición de AnyStyle y spaCy contra el conjunto de oro.
CREATE TABLE corridas_benchmark (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  motor motor_extraccion NOT NULL,
  campo VARCHAR(30) NOT NULL,
  precision_score NUMERIC(5,4),
  recall_score NUMERIC(5,4),
  f1_score NUMERIC(5,4),
  total_muestras INTEGER NOT NULL,
  version_modelo VARCHAR(60),
  ejecutado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Índices sobre llaves foráneas (consultas por usuario, lote y análisis)
CREATE INDEX ON lotes_auditoria (docente_id);
CREATE INDEX ON documentos (propietario_id);
CREATE INDEX ON documentos (lote_id);
CREATE INDEX ON analisis (documento_id);
CREATE INDEX ON reportes_exportados (analisis_id);
CREATE INDEX ON reportes_exportados (generado_por);
CREATE INDEX ON referencias (analisis_id);
CREATE INDEX ON extracciones (referencia_id);
CREATE INDEX ON hallazgos (referencia_id);
CREATE INDEX ON verificaciones (crossref_doi);
CREATE INDEX ON inferencias_nli (verificacion_id);

-- Relación con los usuarios de Supabase Auth y seguridad por fila
ALTER TABLE perfiles ADD CONSTRAINT perfiles_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE perfiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE lotes_auditoria ENABLE ROW LEVEL SECURITY;
ALTER TABLE documentos ENABLE ROW LEVEL SECURITY;
ALTER TABLE analisis ENABLE ROW LEVEL SECURITY;
ALTER TABLE reportes_exportados ENABLE ROW LEVEL SECURITY;
ALTER TABLE referencias ENABLE ROW LEVEL SECURITY;
ALTER TABLE extracciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE hallazgos ENABLE ROW LEVEL SECURITY;
ALTER TABLE registros_crossref ENABLE ROW LEVEL SECURITY;
ALTER TABLE verificaciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE inferencias_nli ENABLE ROW LEVEL SECURITY;
ALTER TABLE referencias_oro ENABLE ROW LEVEL SECURITY;
ALTER TABLE corridas_benchmark ENABLE ROW LEVEL SECURITY;
-- Sin políticas, ninguna tabla es accesible desde el cliente.
-- Las políticas se agregan en migraciones posteriores, módulo por módulo.