# hadolint global ignore=DL3013,DL4006,DL3008,DL3006,DL3009
ARG BUILD_FROM
FROM $BUILD_FROM
WORKDIR /app

RUN apt-get update -y && \
    apt-get install --no-install-recommends -y nano python3 ffmpeg nginx python3-pip python3-dev supervisor && \
    rm /usr/lib/python3.11/EXTERNALLY-MANAGED

RUN curl -sSL https://install.python-poetry.org | python3 -


# Copy root filesystem
COPY /entrypoint /entrypoint
COPY /etc /etc

RUN chmod a+x /entrypoint/entrypoint.sh && \
    chmod a+x /entrypoint/entrypoint.d/*.sh && \
    ln -s /etc/nginx/sites-available/app.conf /etc/nginx/sites-enabled/ && \
    chown -R www-data:www-data /var/lib/nginx/

RUN pip3 install --no-cache-dir setuptools supervisor supervisord-dependent-startup
COPY /src/poetry.lock /app/poetry.lock
COPY /src/pyproject.toml /app/pyproject.toml

WORKDIR /app
RUN /root/.local/share/pypoetry/venv/bin/poetry config virtualenvs.create false && \
    /root/.local/share/pypoetry/venv/bin/poetry install --no-interaction --only main --no-root

COPY /src /app

RUN apt-get clean && rm -rf /var/lib/apt/lists/* && \
    chown www-data:www-data -R /app

ENTRYPOINT ["/bin/bash", "/entrypoint/entrypoint.sh"]