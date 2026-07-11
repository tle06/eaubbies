# ── Build args ────────────────────────────────────────────────────────────────
# BUILD_FROM is injected by HA Supervisor. For standalone builds supply it:
#   docker build --build-arg BUILD_FROM=ghcr.io/home-assistant/aarch64-base-debian:latest
ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-debian:latest
ARG TARGETPLATFORM
ARG BUILDPLATFORM
FROM ${BUILD_FROM} AS runtime

WORKDIR /app

# ── Python env ────────────────────────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ── System dependencies ───────────────────────────────────────────────────────
RUN set -eux; \
    if command -v apt-get >/dev/null 2>&1; then \
      apt-get update -y && \
      apt-get install --no-install-recommends -y \
        nano gettext-base python3 ffmpeg nginx \
        python3-pip python3-dev supervisor cron \
        tesseract-ocr tesseract-ocr-eng && \
      apt-get clean && \
      rm -rf /var/lib/apt/lists/*; \
    elif command -v apk >/dev/null 2>&1; then \
      apk add --no-cache \
        bash nano gettext python3 ffmpeg nginx \
        py3-pip python3-dev supervisor dcron \
        tesseract-ocr tesseract-ocr-data-eng \
        curl; \
    else \
      echo "Unsupported base image: no apt-get/apk found" >&2; \
      exit 1; \
    fi

# ── Entrypoint & config files ─────────────────────────────────────────────────
COPY /entrypoint /entrypoint
COPY /etc /etc

RUN chmod a+x /entrypoint/entrypoint.sh && \
    chmod a+x /entrypoint/entrypoint.d/*.sh && \
    mkdir -p /var/run/nginx

# ── Python dependencies via uv ────────────────────────────────────────────────
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY --from=ghcr.io/astral-sh/uv:latest /uvx /bin/uvx
COPY /src/uv.lock /app/uv.lock
COPY /src/pyproject.toml /app/pyproject.toml
COPY /src/.python-version /app/.python-version
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

ENV PATH="/app/.venv/bin:$PATH"

COPY /src /app

RUN chown -R www-data:www-data /app /var/log/supervisor /var/log/nginx /var/run/nginx

# ── Health check (works both inside HA and standalone) ────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -sf http://unix:/app/ipc.sock; || exit 1

ENTRYPOINT ["/bin/bash", "/entrypoint/entrypoint.sh"]