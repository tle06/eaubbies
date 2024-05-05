#!/bin/bash
echo "Python version"
python3 --version
echo "Start supervisor"
service supervisor start
echo "Start nginx"
nginx -g 'daemon off;error_log /dev/stdout info;'