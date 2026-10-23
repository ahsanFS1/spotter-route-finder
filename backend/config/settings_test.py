import os

os.environ["DEBUG"] = "1"

from .settings import *  # noqa: E402,F401,F403

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "tests"}}
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_CLASSES": []}  # noqa: F405
STATIC_ROOT = BASE_DIR / "tests"  # noqa: F405 (silences the missing-directory warning)
