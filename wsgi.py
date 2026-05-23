"""WSGI entrypoint for production deployments."""
from __future__ import annotations

import os

import app as wikifish_app
from main import DEFAULT_SNAPSHOT_DIR, load_backend


DATA_DIR = os.environ.get('WIKIFISH_DATA_DIR', DEFAULT_SNAPSHOT_DIR)
wikifish_app.configure_backend(load_backend(DATA_DIR))
server = wikifish_app.server

