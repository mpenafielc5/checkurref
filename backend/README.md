# CheckUrRef · Backend

FastAPI + Pydantic, organizado en capas (rutas → servicios → repositorios).

## Comandos (Windows, Git Bash)

```bash
python -m venv .venv                              # solo la primera vez
./.venv/Scripts/python -m pip install -r requirements-dev.txt
cp .env.example .env
./.venv/Scripts/python -m uvicorn app.main:app --reload   # http://localhost:8000/docs
./.venv/Scripts/ruff check .                      # lint
./.venv/Scripts/ruff format .                     # formato
./.venv/Scripts/python -m pytest                  # pruebas
```

En PowerShell, cambiar `./.venv/Scripts/` por `.\.venv\Scripts\`.

## Estructura

```
app/
├── api/routes/     # capa de presentación: rutas HTTP
├── services/       # capa de negocio: casos de uso
├── repositories/   # capa de datos: acceso a Supabase (Repository)
├── schemas/        # DTO de entrada y salida (Pydantic)
├── extraction/     # extractores AnyStyle y spaCy (Strategy)
├── sources/        # clientes de Crossref y OpenAlex (Adapter)
├── verification/   # comparación, similitud y NLI (Singleton)
├── pipeline/       # etapas del análisis (Pipeline)
├── workers/        # procesamiento en segundo plano (Productor-Consumidor)
├── core/           # configuración y validación de la sesión (security.py)
└── main.py         # punto de entrada
```

## Rutas protegidas

El frontend envía el token de la sesión de Supabase en cada petición:
`Authorization: Bearer <access_token>`. La API lo valida con la clave pública
del proyecto (ES256), así que solo necesita `SUPABASE_URL` en el `.env`.

Para proteger una ruta, se declara el usuario de la sesión como parámetro:

```python
from app.api.dependencies import CurrentUser


@router.get("/algo")
def algo(user: CurrentUser) -> ...:  # sin token válido responde 401
    ...
```

`GET /me` es la ruta protegida de referencia: devuelve el id y el correo del
usuario del token. `GET /health` sigue siendo pública.

## Historial, progreso e informe

| Ruta | Para qué |
|---|---|
| `GET /analisis?pagina=n` | Historial de los trabajos del usuario, de 20 en 20, del más reciente al más antiguo (HU-07) |
| `GET /analisis/{id}` | Estado y avance de un análisis, para abrir la pantalla de progreso; los cambios siguientes llegan por Realtime (HU-05) |
| `GET /analisis/{id}/informe` | Informe completo: conteos, índice, campos con más diferencias y, por referencia, texto con sus campos ubicados, veredicto, comparación con el registro, NLI, hallazgos y referencia corregida (HU-06, HU-19) |

Cada usuario ve solo sus análisis: uno ajeno responde 404, igual que uno que no
existe. El informe de un análisis en curso o con error responde 409 con el
motivo. El informe llega completo y el navegador filtra por veredicto y pagina
de 10 en 10: un trabajo tiene decenas de referencias. Capas:
`app/api/routes/analyses.py` → `app/services/report_service.py` →
`app/repositories/reports.py`; `app/reports/highlight.py` ubica los campos en el
texto original sin alterarlo.

## Extracción de la sección de referencias

`app/pipeline/references_section.py` lee el PDF con PyMuPDF, quita encabezados
y números de página, une las líneas cortadas y devuelve las líneas de la sección
Referencias (o Bibliografía, References…), cada una con su página y su sangría.
Las pruebas usan PDF generados en el momento (`tests/pdf_factory.py`).

## Separación de las referencias y norma detectada

`app/pipeline/segmentation.py` separa esas líneas en referencias: por el número
[n] (IEEE), por la sangría (francesa o de primera línea, frecuente en los
trabajos) o, si la lista no tiene sangría, por el patrón autor-año.
`app/pipeline/norm_detection.py` reconoce la norma de cada referencia por sus
rasgos (APA, IEEE o DESCONOCIDA) y la de la lista completa (también MIXTA).

Una entrada cuya separación no se puede confirmar no detiene el análisis: se
guarda con el hallazgo informativo `SEPARACION_NO_CONFIRMADA`
(`app/repositories/references.py`). Como con "No verificable", el mensaje dice
qué no pudo confirmar el sistema, sin culpar al estudiante: la causa puede ser
la lectura del PDF. En el informe, la norma DESCONOCIDA se muestra como "Norma
no identificada".

## Extracción de los campos

`app/extraction` implementa el patrón Strategy: `AnyStyleExtractor` (modelo
entrenado, ejecuta `anystyle-cli` de Ruby como comando externo) y
`SpacyExtractor` (reglas sobre el tokenizador y el `Matcher` de spaCy) cumplen
la misma interfaz, `extract(referencia) -> campos`. `EXTRACTION_ENGINE` elige
cuál usa el análisis. Si un extractor falla con una referencia, solo esa queda
marcada y el documento continúa. La prueba con AnyStyle real se omite si
`anystyle` no está instalado, salvo en el CI, que instala Ruby y `anystyle-cli`.

## Worker de análisis

`app/workers/analysis_worker.py` arranca junto con la API (si hay conexión con
Supabase y `WORKER_ENABLED=true`): toma de la tabla `t_analisis` el trabajo más
antiguo "en_cola" y lo procesa en un hilo aparte (`app/services/analysis_service.py`):
descarga el PDF, separa las referencias, detecta la norma, extrae los campos y
verifica cada referencia, actualizando `estado` y `progreso`. Un error en un
documento lo marca como "error" con su mensaje y la cola sigue. Si el servidor se
reinicia a mitad de un análisis, al volver a iniciar ese análisis regresa a la
cola. Si `anystyle-cli` no está instalado, se usa spaCy y queda registrado en
`t_analisis.extractor_principal`.

La verificación (etapa "verificando", de 30 a 95 % del avance) consulta las
referencias a la vez, con los límites de cada fuente, y guarda el resultado con
`app/repositories/verifications.py`: una fila de `t_verificaciones` por referencia
con veredicto y su referencia corregida (`referencia_corregida`, migración 4: hay
que aplicarla antes de usar esta versión del backend), lo que respondió el NLI
por campo (`t_inferencias_nli`), un hallazgo
de veracidad por cada campo distinto (`t_hallazgos`, con el valor citado y el
oficial; `app/verification/findings.py`) y `t_analisis.indice_veracidad`. Un error
de consulta o un error interno en una referencia no tiene fila en
`t_verificaciones`: queda su hallazgo informativo y no cuenta en el índice (RNF09,
RNF10). El modelo NLI se carga al arrancar; si falta, la API funciona pero el
worker no inicia y lo avisa en la terminal.

## Estándar de oro

`app/benchmark/gold_set.py` y `scripts/gold_set.py` preparan, validan, comparan
entre anotadores, alteran y cargan el estándar de oro (T09) en
`m_referencias_oro`. Uso: `./.venv/Scripts/python -m scripts.gold_set --help`.

## Consulta de Crossref y OpenAlex

`app/sources` implementa el patrón Adapter: `CrossrefClient` (fuente principal)
y `OpenAlexClient` (respaldo) traducen sus respuestas a `SourceRecord`.
`ReferenceLookup` busca por DOI (normalizado antes) y, si no hay DOI o nadie lo
tiene, por título y autor. Limita la concurrencia (3 consultas simultáneas a
Crossref) y el ritmo, y reintenta con espera exponencial ante 429, 502 o 503,
respetando `Retry-After`. Solo un 404 significa "no encontrada": si alguna fuente
no respondió, el resultado es un error de consulta y no cuenta en el índice.
Las obras con DOI se guardan en la caché `m_registros_crossref`
(`app/repositories/record_cache.py`).

Variables: `CROSSREF_MAILTO` (correo de contacto, para el polite pool de
Crossref) y `OPENALEX_API_KEY` (opcional, gratuita).

## Modelo NLI

`app/verification/nli.py` ejecuta `Recognai/bert-base-spanish-wwm-cased-xnli`
en ONNX int8 con `onnxruntime` (sin PyTorch) y devuelve las probabilidades de
implicación, neutralidad y contradicción de cada par (premisa, hipótesis).
`get_nli_model` lo carga una sola vez (Singleton). El orden de las etiquetas se
lee de `config.json`: en este modelo es contradicción, neutral, implicación.

El modelo no se sube al repositorio (Git ignora `models/`). Se genera una vez,
en un entorno aparte porque la exportación sí necesita PyTorch:

```bash
py -3.10 -m venv .venv-export
./.venv-export/Scripts/python -m pip install -r requirements-export.txt
./.venv-export/Scripts/python -m scripts.export_nli
```

El script deja `model.onnx` (unos 111 MB), `tokenizer.json` y `config.json` en
`models/nli/` (`NLI_MODEL_DIR`) y compara el modelo cuantizado con el original.
Las pruebas con el modelo real se omiten si la carpeta no existe.

## Motor de decisión

`app/verification/decision.py` recibe los campos de la referencia y lo que
encontró la búsqueda, y devuelve el veredicto con la comparación de cada campo y
las inferencias NLI. No consulta nada: son funciones puras, con el modelo NLI
como dependencia. `app/verification/verifier.py` une la búsqueda con el motor y,
si la búsqueda por título trae otro año, vuelve a pedir la obra por DOI para
conocer el año del número impreso.

- Año, DOI, volumen y páginas se comparan de forma directa; título, autores y
  revista por similitud (`rapidfuzz`), con tolerancia a tildes, abreviaturas
  ("Rev. Andina") y nombres completos de OpenAlex.
- El NLI decide los títulos dudosos y queda guardado para explicar el veredicto.
- Contradicción: el DOI citado lleva a otra obra (otro título y otros autores).
  Un título igual con otros autores es Con discrepancias, para no tomar un error
  del extractor como otra obra; los autores iguales con otro título también (el
  título pudo citarse traducido). Las reglas completas están en la arquitectura.
- Un error de consulta no tiene veredicto (`None`) y no cuenta en el índice.

## Referencia corregida

`app/verification/corrected.py` arma la referencia en APA 7 o IEEE (según la
norma de cada referencia) con los datos del registro, para el botón de copiar
(HU-19). Corrige solo lo que está mal: un campo que coincide queda como lo
escribió el estudiante, y uno que difiere o falta se toma del registro y se marca
como cambiado. Devuelve segmentos con el campo, la cursiva y si cambió, para que
el informe resalte los cambios. En IEEE conserva el número [n]; en ambas normas,
el conector que usó el estudiante ("y", "&" o ", &"; "and" o "y"). Solo se ofrece
si es seguro que el registro es la obra citada: DOI que lleva a ella o el mismo
título. Formatos según normas-apa.org y la guía de referencias de IEEE (2025).
- Los umbrales (`Thresholds`) son iniciales; T18 los calibra con el estándar de oro.

Para probar con PDF reales sin subirlos al repositorio, ponerlos en
`backend/pdf-locales/` (Git ignora esa carpeta) y ejecutar:

```bash
./.venv/Scripts/python -m scripts.inspect_pdf pdf-locales/*.pdf
```

Regla de las capas: una ruta solo llama a servicios, un servicio solo llama a
repositorios y a los módulos de dominio, y nadie salta capas.
Ver [`../docs/arquitectura.md`](../docs/arquitectura.md).

## Despliegue (T15) y ping diario (T21)

La API corre en un Space Docker de Hugging Face. `Dockerfile` tiene dos etapas:
la primera genera el modelo NLI con `scripts/export_nli.py` y las versiones
fijas de `requirements-export.txt` (PyTorch solo vive ahí); la segunda instala
Ruby, anystyle-cli y `requirements.txt`, copia el modelo y arranca uvicorn en el
puerto 7860 con el usuario 1000, como pide Hugging Face.

`.github/workflows/deploy-backend.yml` sube `backend/` al Space en cada cambio
en `main` (o a mano desde Actions). Necesita en el repositorio de GitHub la
variable `HF_SPACE` (`usuario/nombre-del-space`) y el secreto `HF_TOKEN` (token
de escritura). Sin `HF_SPACE`, el flujo no corre.

En el Space (Settings > Variables and secrets), como **secretos**:
`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `CROSSREF_MAILTO`,
`OPENALEX_API_KEY` y `CORS_ORIGINS` (JSON con la dirección del frontend en
Vercel). El Space debe ser público para que el navegador llegue a la API.

`.github/workflows/ping.yml` consulta cada día `GET /health` y Supabase para que
no se suspendan. Necesita las variables `API_URL` (dirección del Space, por
ejemplo `https://usuario-nombre.hf.space`), `SUPABASE_URL` y
`SUPABASE_PUBLISHABLE_KEY`.
