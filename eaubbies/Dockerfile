# hadolint global ignore=DL3013,DL4006,DL3008,DL3006,DL3009
ARG BUILD_FROM

FROM $BUILD_FROM AS runtime

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update -y && \
    apt-get install --no-install-recommends -y nano gettext-base python3 ffmpeg nginx python3-pip python3-dev supervisor cron tesseract-ocr tesseract-ocr-eng && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


COPY /entrypoint /entrypoint
COPY /etc /etc

RUN chmod a+x /entrypoint/entrypoint.sh && \
    chmod a+x /entrypoint/entrypoint.d/*.sh && \
    mkdir -p /var/run/nginx

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY /src/uv.lock /app/uv.lock
COPY /src/pyproject.toml /app/pyproject.toml
COPY /src/.python-version /app/.python-version
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

ENV PATH="/app/.venv/bin:$PATH"

COPY /src /app

RUN chown -R www-data:www-data /app /var/log/supervisor /var/log/nginx /var/run/nginx

ENTRYPOINT ["/bin/bash", "/entrypoint/entrypoint.sh"]