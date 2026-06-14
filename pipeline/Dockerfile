# On-demand dataset generation. NOT part of `docker compose up` — invoked via the
# `data` profile (see docker-compose.yml and docs/adr/0001). Writes into /pipeline/out,
# which is bind-mounted to the host so the backend can serve the result.
#
# Runs as a non-root user. Because it writes to host bind mounts, compose passes the
# host UID/GID via `user:` so generated files aren't root-owned on the host.
FROM python:3.12-slim@sha256:d764629ce0ddd8c71fd371e9901efb324a95789d2315a47db7e4d27e78f1b0e9

RUN useradd -u 1000 -m pipeline

WORKDIR /pipeline

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY . .

USER pipeline

ENTRYPOINT ["python", "build_dataset.py"]
