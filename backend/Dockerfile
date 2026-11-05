# Imagen de la API para Hugging Face Spaces (T15).
#
# Etapa 1: genera el modelo NLI en ONNX int8 (T12) con scripts/export_nli.py.
# PyTorch solo vive en esta etapa; la imagen final copia el modelo terminado.
# Solo se copian los archivos que usa la exportación: si cambia otra parte del
# código, Docker reutiliza el modelo ya generado.
FROM python:3.11-slim AS nli

WORKDIR /build
COPY requirements-export.txt .
RUN pip install --no-cache-dir -r requirements-export.txt
COPY app/__init__.py app/__init__.py
COPY app/verification/__init__.py app/verification/nli.py app/verification/
COPY scripts/__init__.py scripts/export_nli.py scripts/
RUN python -m scripts.export_nli --salida models/nli

# Etapa 2: la API, con Ruby y anystyle-cli para el extractor principal (T07).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production

# Las herramientas de compilación solo hacen falta para instalar anystyle-cli.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ruby ruby-dev build-essential \
    && gem install anystyle-cli --no-document \
    && apt-get purge -y --auto-remove ruby-dev build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && anystyle --version

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Hugging Face Spaces ejecuta el contenedor con el usuario 1000.
RUN useradd --create-home --uid 1000 user
USER user
WORKDIR /home/user/app

COPY --chown=user --from=nli /build/models/nli models/nli
COPY --chown=user app app

EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers", "--forwarded-allow-ips", "*"]
