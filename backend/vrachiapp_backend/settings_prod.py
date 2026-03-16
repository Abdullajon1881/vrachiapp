from .settings import *  # noqa

# Production overrides

DEBUG = False

# Restrict allowed hosts to production domains and local loopback
ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "healzy.uz",
    "www.healzy.uz",
    ".railway.app",
    ".up.railway.app",
]

# CORS/CSRF origins for production SPA and API endpoints
CORS_ALLOWED_ORIGINS = [
    "https://healzy.uz",
    "https://www.healzy.uz",
    "https://vrachiapp-production.up.railway.app",
]

CSRF_TRUSTED_ORIGINS = [
    "https://healzy.uz",
    "https://www.healzy.uz",
    "https://vrachiapp-production.up.railway.app",
]

