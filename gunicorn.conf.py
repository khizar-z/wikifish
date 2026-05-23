"""Gunicorn settings for WikiFish production deployments."""
from __future__ import annotations

import os


bind = os.environ.get('WIKIFISH_BIND', '127.0.0.1:8050')
workers = int(os.environ.get('WIKIFISH_WORKERS', '1'))
timeout = int(os.environ.get('WIKIFISH_TIMEOUT', '180'))
graceful_timeout = int(os.environ.get('WIKIFISH_GRACEFUL_TIMEOUT', '30'))
preload_app = os.environ.get('WIKIFISH_PRELOAD', 'true').lower() in {'1', 'true', 'yes', 'on'}
accesslog = '-'
errorlog = '-'
