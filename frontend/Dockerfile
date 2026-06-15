# Multi-stage: build the static bundle with Node/pnpm, serve it with nginx.
#
# Build context is the REPO ROOT (see docker-compose.yml), not frontend/. This
# is deliberate: the repo is a pnpm workspace whose single source of truth is the
# root pnpm-lock.yaml. Building from frontend/ in isolation would need a second,
# standalone lockfile that silently drifts from the one dev/CI actually resolve —
# which is exactly what broke the docker gate before. One lockfile, no drift.
#
# --- build stage ---
FROM node:24-alpine@sha256:fb71d01345f11b708a3553c66e7c74074f2d506400ea81973343d915cb64eef0 AS build

WORKDIR /app
# pnpm comes via corepack; the exact version is pinned by the "packageManager"
# field in the root package.json, so corepack resolves it automatically.
RUN corepack enable

# Copy the workspace manifests + lockfile first so the install layer stays cached
# on source-only changes, and install from the lockfile for reproducible builds.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY frontend/package.json frontend/
RUN pnpm install --frozen-lockfile --filter ./frontend

# Copy the frontend source and build the static bundle.
COPY frontend/ frontend/
RUN pnpm --filter ./frontend build

# --- serve stage ---
# Rootless nginx: runs as uid 101 and listens on :8080 (see nginx.conf).
FROM nginxinc/nginx-unprivileged:1.27-alpine@sha256:65e3e85dbaed8ba248841d9d58a899b6197106c23cb0ff1a132b7bfe0547e4c0

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html

EXPOSE 8080

# Use 127.0.0.1, not localhost: the read-only rootfs skips nginx's
# 10-listen-on-ipv6-by-default.sh entrypoint script (it can't edit the conf), so
# nginx binds IPv4 only. busybox wget would try localhost -> ::1 first and get a
# connection refused, marking the container permanently unhealthy.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/ >/dev/null 2>&1 || exit 1
