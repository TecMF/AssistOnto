import os

workers = int(os.environ.get('GUNICORN_PROCESSES', '8'))

threads = int(os.environ.get('GUNICORN_THREADS', '2'))

bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8080')

accesslog = os.environ.get('GUNICORN_ACCESSLOG', '-')

loglevel = os.environ.get('GUNICORN_LOGLEVEL', 'info')
