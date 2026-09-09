"""Vercel serverless entrypoint for the Django portal.

Vercel's Python runtime imports this module and looks for a WSGI/ASGI callable
named ``app``. The repository keeps the Django project one level down (this
file lives in ``cosomis/api/``, the project package in ``cosomis/cosomis/``),
so the project root goes on ``sys.path`` before Django is imported.
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cosomis.settings")

from cosomis.wsgi import application  # noqa: E402  (path setup must run first)

app = application
