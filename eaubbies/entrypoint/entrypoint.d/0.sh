#!/bin/bash
echo "[EXECUTION] 0.sh file"

# INGRESS_PORT: injected by HA Supervisor at runtime, fallback for standalone
export INGRESS_PORT="${INGRESS_PORT:-8099}"
echo "[INFO] INGRESS_PORT : $INGRESS_PORT"

if [ -n "${SUPERVISOR_TOKEN}" ]; then
    echo "[INFO] Running as Home Assistant add-on — restricting to Supervisor IP"
    export INGRESS_ACL="allow 172.30.32.2;
    deny all;"
    # HA Supervisor mounts the persistent share at /config
    export CONFIG_PATH="${CONFIGURATION_PATH:-"/config"}"
else
    echo "[INFO] Running standalone — no IP restriction applied"
    export INGRESS_ACL=""
    # Standalone: data volume is mounted at /data
    export CONFIG_PATH="${CONFIGURATION_PATH:-"/data"}"
fi

echo "[INFO] CONFIG_PATH : $CONFIG_PATH"

start_web() {
    echo "-------------------------------------"
    echo "[PREPARATION] Create NGINX configuration file at /etc/nginx/sites-available/app.conf"
    echo "NGINX will use PORT: $INGRESS_PORT and ENTRY: $INGRESS_ENTRY"

    envsubst "\$INGRESS_PORT \$INGRESS_ACL" \
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
