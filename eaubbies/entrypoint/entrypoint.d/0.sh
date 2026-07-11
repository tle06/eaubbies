#!/bin/bash
echo "[EXECUTION] 0.sh file"

# If PORT is unset or empty, default to 8099
export INGRESS_PORT="${INGRESS_PORT:-8099}"
echo "[INFO] Target port is set to: $INGRESS_PORT"

start_web() {
    echo "-------------------------------------"
    echo "[PREPARATION] Create NGINX configuration file at /etc/nginx/sites-available/app.conf"


    echo "NGINX will use the PORT: $INGRESS_PORT"
    envsubst "\$INGRESS_PORT" < /etc/nginx/conf.d/app.template > /etc/nginx/sites-available/app.conf


    echo "[PREPARATION] Activate NGINX configuration file"
    # Added -f (force) to prevent errors if the symlink already exists on container restart
    ln -sf /etc/nginx/sites-available/app.conf /etc/nginx/sites-enabled/
    
    echo "[PREPARATION] Finished"
    echo "Server will start now with the following command:"
    echo "/usr/bin/supervisord -c /etc/supervisor/supervisord.conf"
    echo "-------------------------------------"
    /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
}

echo "Starting server as web"
start_web