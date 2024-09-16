# Home Assistant Add-on: Eaubbies

![Supports aarch64 Architecture][aarch64-shield]
![Supports amd64 Architecture][amd64-shield]

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg

# Local dev

The project use [UV](https://docs.astral.sh/uv/) package manager.

## Init the project

```cmd
git clone https://github.com/tle06/eaubbies.git
cd eaubbies/eaubbies/src
uv venv
uv sync --frozen
uv run -- flask run --debug
```

# Docker

## Build local

```cmd
cd eaubbies
docker build --build-arg BUILD_FROM="homeassistant/amd64-base-debian:bookworm" -t eaubbies:local .
```

## Home assistant build

```cmd
docker run \
	--rm \
	--privileged \
	-v ~/.docker:/root/.docker \
	-v .:/data \
    ghcr.io/home-assistant/amd64-builder:latest \
		--all \
		-t /data/eaubbies
```

## Run local build

```cmd
docker run --name test --rm -p 8099:8099 eaubbies:local
```

# Docker-compose

The compose will start the eaubbies app by default (port 8099)

```cmd
docker-compose up
```

You can also start home-assistant container (port 8123) on top of the eaubbies app

```cmd
docker-compose --profile all up
```

## Docker-compose build

```cmd
docker-compose build
```