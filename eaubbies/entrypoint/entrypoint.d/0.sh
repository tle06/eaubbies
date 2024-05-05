#!/bin/bash
python --version
service supervisor start
nginx -g 'daemon off;error_log /dev/stdout debug;'