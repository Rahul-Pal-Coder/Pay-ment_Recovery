import os
import sys

# Ensure parent directory is in sys.path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

try:
    from .celery import app as celery_app
except ImportError:
    try:
        from config.celery import app as celery_app
    except ImportError:
        celery_app = None

if celery_app:
    __all__ = ('celery_app',)
else:
    __all__ = ()
