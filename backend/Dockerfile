# Lean production image for the FastAPI backend (no --reload).
# Serves whatever harmonized dataset is mounted at /data (see docker-compose.yml).
FROM python:3.12-slim@sha256:d764629ce0ddd8c71fd371e9901efb324a95789d2315a47db7e4d27e78f1b0e9

WORKDIR /app

# duckdb / pyarrow / pandas ship manylinux wheels — no build toolchain needed.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Run as an unprivileged user (the app only reads a bind-mounted dataset).
RUN useradd -u 1001 -m appuser
USER appuser

# Dataset is bind-mounted read-only at /data by compose; point the loader there.
ENV DATASET_PARQUET=/data/dataset_concentration_patrimoine_fr.parquet \
  DATASET_CSV=/data/dataset_concentration_patrimoine_fr.csv

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
