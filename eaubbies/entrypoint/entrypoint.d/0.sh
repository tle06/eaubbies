#!/bin/bash
echo "[EXECUTION] 0.sh file"

# INGRESS_PORT: injected by HA Supervisor at runtime, fallback for standalone
export INGRESS_PORT="${INGRESS_PORT:-8099}"
# INGRESS_ENTRY: ingress path prefix injected by HA Supervisor, fallback for standalone
export INGRESS_ENTRY="${INGRESS_ENTRY:-/}"

echo "[INFO] INGRESS_PORT : $INGRESS_PORT"
echo "[INFO] INGRESS_ENTRY: $INGRESS_ENTRY"

start_web() {
    echo "-------------------------------------"
    echo "[PREPARATION] Create NGINX configuration file at /etc/nginx/sites-available/app.conf"
    echo "NGINX will use PORT: $INGRESS_PORT and ENTRY: $INGRESS_ENTRY"

    envsubst "\$INGRESS_PORT \$INGRESS_ENTRY" \
        < /etc/nginx/conf.d/app.template \
        > /etc/nginx/sites-available/app.conf

    echo "[PREPARATION] Activate NGINX configuration file"
    # -f (force) to prevent errors if the symlink already exists on container restart
    ln -sf /etc/nginx/sites-available/app.conf /etc/nginx/sites-enabled/

    echo "[PREPARATION] Finished"
    echo "Server will start now with the following command:"
    echo "/usr/bin/supervisord -c /etc/supervisor/supervisord.conf"
    echo "-------------------------------------"
    /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
}

echo "Starting server as web"
start_web
