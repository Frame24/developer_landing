# ruff: noqa: E501
"""Render / free PaaS settings: SQLite, no Redis, Whitenoise."""

from .base import *  # noqa: F403
from .base import BASE_DIR
from .base import DATABASES
from .base import SPECTACULAR_SETTINGS
from .base import env

DEBUG = env.bool("DJANGO_DEBUG", default=False)
SECRET_KEY = env("DJANGO_SECRET_KEY", default="change-me-in-production-please-use-a-long-secret")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["*"])

DATABASES["default"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": str(BASE_DIR / "db.sqlite3"),
    "ATOMIC_REQUESTS": True,
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "developer-landing",
    },
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=60)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=True,
)
SECURE_CONTENT_TYPE_NOSNIFF = True

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

ADMIN_URL = env("DJANGO_ADMIN_URL", default="admin/")

CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=True)

SPECTACULAR_SETTINGS["SERVERS"] = [
    {"url": env("PUBLIC_API_URL", default="https://localhost"), "description": "Deployed API"},
]
