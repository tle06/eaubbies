#!/bin/bash
echo "Python version"
python3 --version
echo "Fix nginx file access"
chown -R www-data:www-data /var/lib/nginx/
echo "Start supervisor"
service supervisor start
echo "Start nginx"
nginx -g 'daemon off;error_log /dev/stdout info;'