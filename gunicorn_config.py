import os

# Gunicorn configuration for Render deployment
workers = int(os.environ.get('GUNICORN_WORKERS', 4))
threads = int(os.environ.get('GUNICORN_THREADS', 1))
timeout = int(os.environ.get('GUNICORN_TIMEOUT', 30))
bind = f"0.0.0.0:{os.environ.get('PORT', 8000)}"
worker_class = "gthread"
worker_tmp_dir = "/dev/shm"  # Use memory for temporary files
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log errors to stdout
loglevel = "info"
