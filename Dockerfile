# https://developers.home-assistant.io/docs/add-ons/configuration#add-on-dockerfile
ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache python3

# Copy root filesystem
COPY /rootfs /
RUN chmod a+x /usr/bin/start.sh

CMD [ "/usr/bin/start.sh" ]