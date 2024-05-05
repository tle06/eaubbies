# Home Assistant Add-on: Eaubbies

![Supports aarch64 Architecture][aarch64-shield]
![Supports amd64 Architecture][amd64-shield]
![Supports armhf Architecture][armhf-shield]
![Supports armv7 Architecture][armv7-shield]
![Supports i386 Architecture][i386-shield]

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[armhf-shield]: https://img.shields.io/badge/armhf-yes-green.svg
[armv7-shield]: https://img.shields.io/badge/armv7-yes-green.svg
[i386-shield]: https://img.shields.io/badge/i386-yes-green.svg


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
