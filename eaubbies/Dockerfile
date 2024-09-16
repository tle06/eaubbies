# hadolint global ignore=DL3013,DL4006,DL3008,DL3006,DL3009
ARG BUILD_FROM

FROM python:3.12-slim AS dependencies
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=/src/uv.lock,target=uv.lock \
    --mount=type=bind,source=/src/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

FROM $BUILD_FROM AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update -y && \
    apt-get install --no-install-recommends -y nano python3 ffmpeg nginx python3-pip python3-dev supervisor cron && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm /usr/lib/python3.11/EXTERNALLY-MANAGED

COPY --from=dependencies /bin/uv /bin/uv
COPY /entrypoint /entrypoint
COPY /etc /etc

RUN chmod a+x /entrypoint/entrypoint.sh && \
    chmod a+x /entrypoint/entrypoint.d/*.sh && \
    ln -s /etc/nginx/sites-available/app.conf /etc/nginx/sites-enabled/

WORKDIR /app

COPY /src/uv.lock /app/uv.lock
COPY /src/pyproject.toml /app/pyproject.toml

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

ENV PATH="/app/.venv/bin:$PATH"

COPY /src /app

RUN mkdir -p /var/lib/nginx/body && \
    chown -R www-data:www-data /app && \
    chown -R www-data:www-data /var/lib/nginx/

ENTRYPOINT ["/bin/bash", "/entrypoint/entrypoint.sh"]