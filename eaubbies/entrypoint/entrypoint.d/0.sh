#!/bin/bash
echo "[EXCUTION] 0.sh file"

start_web() {

    echo "-------------------------------------"
    echo "[PREPARATION] Create NGINX configuration file at /etc/nginx/sites-available/app.conf"
    echo "NGINX will use the PORT: $PORT"
    envsubst "\$PORT" < /etc/nginx/conf.d/app.template > /etc/nginx/sites-available/app.conf

    echo "[PREPARATION] Activate NGINX configuration file"
    ln -s /etc/nginx/sites-available/app.conf /etc/nginx/sites-enabled/
    echo "[PREPARATION] Finished"
    echo "Server will start now with the following command:"
    echo "/usr/bin/supervisord -c /etc/supervisor/supervisord.conf"
    echo "-------------------------------------"
    /usr/bin/supervisord -c /etc/supervisor/supervisord.conf

}

echo "Starting server as web"
start_web


