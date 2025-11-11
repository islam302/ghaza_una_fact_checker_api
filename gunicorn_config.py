"""Gunicorn configuration file."""
import multiprocessing

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
timeout = 30
keepalive = 2

# Logging
accesslog = "-"  # stdout
errorlog = "-"  # stderr
loglevel = "info"

# Process naming
proc_name = "ghaza_una_fact_checker_api"

# Preload app
preload_app = True

# Restart workers after this many requests
max_requests = 1000
max_requests_jitter = 50

