# Stage 1: Build dependencies
FROM python:3.12.3-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/app/.local -r requirements.txt


# Stage 2: Production runtime
FROM python:3.12.3-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python dependencies from builder
COPY --from=builder /app/.local /app/.local
ENV PATH=/app/.local/bin:$PATH
ENV PYTHONPATH=/app/.local/lib/python3.12/site-packages
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir --upgrade --force-reinstall -r requirements.txt -c constraints.txt
RUN pip install --no-cache-dir --upgrade --force-reinstall pydantic==2.7.1 langgraph==0.0.45 langchain-core==0.1.52 langsmith==0.1.63


# Create a non-root system user for security
RUN useradd -u 10001 lexai && chown -R lexai:lexai /app
USER lexai

COPY --chown=lexai:lexai . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
