# Single-stage build: install directly into the runtime image.
# Two-stage builds with --prefix + PYTHONPATH conflict with a second full pip install.
FROM python:3.12.3-slim

WORKDIR /app

# System dependencies: build tools for psycopg2/cffi, runtime libs for pq, OCR, PDF rasterization
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libpq5 \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt

# Create a non-root system user for security
RUN useradd -u 10001 lexai && chown -R lexai:lexai /app
USER lexai

COPY --chown=lexai:lexai . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
