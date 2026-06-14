# Multi-stage: build the static bundle with Node/pnpm, serve it with nginx.
# --- build stage ---
FROM node:24-alpine@sha256:fb71d01345f11b708a3553c66e7c74074f2d506400ea81973343d915cb64eef0 AS build

WORKDIR /app
# pnpm comes via corepack; the exact version is pinned by the "packageManager"
# field in package.json, so corepack resolves it automatically on first use.
RUN corepack enable

# Copy the manifest + lockfile first so the install layer stays cached on
# source-only changes, and install from the lockfile for reproducible builds.
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

# --- serve stage ---
# Rootless nginx: runs as uid 101 and listens on :8080 (see nginx.conf).
FROM nginxinc/nginx-unprivileged:1.27-alpine@sha256:65e3e85dbaed8ba248841d9d58a899b6197106c23cb0ff1a132b7bfe0547e4c0

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost:8080/ >/dev/null 2>&1 || exit 1
