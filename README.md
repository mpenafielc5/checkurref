# CheckUrRef

**Aplicativo web de auditoría y validación de referencias bibliográficas en
documentos académicos mediante Inferencia de Lenguaje Natural.**

Caso de estudio de la carrera de Ingeniería de Software de la Universidad Estatal
de Milagro (UNEMI).

## Qué hace

El estudiante o el docente sube el PDF de un trabajo académico. CheckUrRef extrae
las referencias (APA e IEEE), las separa en sus campos, consulta los metadatos
registrados en Crossref (con OpenAlex como respaldo) y emite un veredicto por
referencia:

| Veredicto | Significado |
|---|---|
| Verificada | Coincide con el registro |
| Con discrepancias | La obra existe, pero algún campo está alterado |
| Contradicción | El DOI no existe o los datos contradicen el registro |
| Sin respaldo | No se encontró ninguna obra candidata |
| No verificable | Libro, tesis o sitio web fuera de la cobertura de las fuentes |

## Tecnologías

| Capa | Tecnología |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Backend | Python, FastAPI, Pydantic |
| Extracción | PyMuPDF, AnyStyle, spaCy |
| Inferencia | BERT en español (XNLI) en formato ONNX, en CPU |
| Datos | Supabase: PostgreSQL, Auth, Storage, Realtime |
| Despliegue | Vercel y Hugging Face Spaces |

## Estructura

```
frontend/   aplicación web (Next.js)
backend/    API y motor de verificación (FastAPI, en capas)
supabase/   migraciones de la base de datos (PostgreSQL)
```

## Cómo ejecutarlo

Requisitos: Node.js 24, Python 3.10 o superior y un proyecto de Supabase.

**1. Base de datos.** En el SQL Editor de Supabase, ejecutar en orden los
archivos de `supabase/migrations/`.

**2. Backend** (desde `backend/`):

```bash
python -m venv .venv
./.venv/Scripts/python -m pip install -r requirements-dev.txt
cp .env.example .env                  # completar SUPABASE_URL
./.venv/Scripts/python -m uvicorn app.main:app --reload   # http://localhost:8000/docs
```

**3. Frontend** (desde `frontend/`):

```bash
npm install
cp .env.example .env.local            # completar las variables de Supabase y de la API
npm run dev                           # http://localhost:3000
```

En Linux o macOS, cambiar `./.venv/Scripts/` por `./.venv/bin/`.

## Pruebas

```bash
cd backend && ./.venv/Scripts/python -m pytest
cd frontend && npm run test
```

Cada cambio pasa por integración continua (GitHub Actions): lint, formato,
tipos, pruebas y compilación del frontend y del backend.

## Autores

- Miguel Angel Peñafiel Cadena
- Jackson Enrique Reyes Ibarra
