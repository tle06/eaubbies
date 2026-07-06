# Gunicorn configuration file
# https://docs.gunicorn.org/en/stable/configure.html#configuration-file
# https://docs.gunicorn.org/en/stable/settings.html

from environs import Env
import multiprocessing

env = Env()
env.read_env()

bind = "unix:/app/ipc.sock"
daemon = env.bool("GUNICORN_DAEMON", False)
workers = env.int("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1)
threads = env.int("GUNICORN_THREADS", 2)
log_file = "-"
loglevel = env.str("LOGLEVEL", "info").lower()
capture_output = True
wsgi_app = "app:app"
timeout = env.int("GUNICORN_TIMEOUT", 600)
preload_app = env.bool("GUNICORN_PRELOAD_APP", True)
control_socket_disable = env.bool("GUNICORN_CONTROL_SOCKET_DISABLE", True)
