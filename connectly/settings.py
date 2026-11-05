import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

DEBUG = os.environ.get("DJANGO_DEBUG", "1" if not os.environ.get("RENDER") else "0") == "1"
DJANGO_SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "").strip()
if not DEBUG and not DJANGO_SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be set whenever DJANGO_DEBUG=False."
    )
SECRET_KEY = DJANGO_SECRET_KEY or "connectly-local-development-key-change-before-deploying"
MONGODB_URI = os.environ.get("MONGODB_URI", "").strip()
MONGODB_DATABASE = os.environ.get("MONGODB_DATABASE", "connectly").strip()
DATABASE_BACKEND = os.environ.get("DJANGO_DATABASE", "mongodb").strip().lower()
if DATABASE_BACKEND not in {"mongodb", "sqlite"}:
    raise ImproperlyConfigured("DJANGO_DATABASE must be either 'mongodb' or 'sqlite'.")
MONGODB_ENABLED = DATABASE_BACKEND == "mongodb"
if MONGODB_ENABLED and not MONGODB_URI:
    raise ImproperlyConfigured(
        "MONGODB_URI is required when DJANGO_DATABASE=mongodb. "
        "Set it in the environment or local .env, or explicitly set DJANGO_DATABASE=sqlite for local development."
    )
if MONGODB_ENABLED and not MONGODB_URI.startswith(("mongodb://", "mongodb+srv://")):
    raise ImproperlyConfigured("MONGODB_URI must be a MongoDB connection URI.")
if MONGODB_ENABLED and not MONGODB_DATABASE:
    raise ImproperlyConfigured("MONGODB_DATABASE cannot be empty.")
if os.environ.get("RENDER") and not MONGODB_ENABLED:
    raise ImproperlyConfigured("Set MONGODB_URI in the Render environment.")
if os.environ.get("RENDER") and not os.environ.get("DJANGO_SECRET_KEY"):
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY in the Render environment.")
if os.environ.get("RENDER") and DEBUG:
    raise ImproperlyConfigured("Set DJANGO_DEBUG=False in the Render environment.")
render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost" if DEBUG else ""
    ).split(",")
    if host.strip()
]
if render_hostname and render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_hostname)
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "Set DJANGO_ALLOWED_HOSTS or configure RENDER_EXTERNAL_HOSTNAME in production."
    )

INSTALLED_APPS = [
    *(
        [
            "connectly.mongodb_apps.MongoAdminConfig",
            "connectly.mongodb_apps.MongoAuthConfig",
            "connectly.mongodb_apps.MongoContentTypesConfig",
        ]
        if MONGODB_ENABLED
        else [
            "django.contrib.admin",
            "django.contrib.auth",
            "django.contrib.contenttypes",
        ]
    ),
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "social.apps.SocialConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "connectly.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "social.context_processors.social_context",
            ],
        },
    },
]

WSGI_APPLICATION = "connectly.wsgi.application"

if MONGODB_ENABLED:
    DATABASES = {
        "default": {
            "ENGINE": "django_mongodb_backend",
            "HOST": MONGODB_URI,
            "NAME": MONGODB_DATABASE,
            "OPTIONS": {
                "serverSelectionTimeoutMS": 10000,
                "retryWrites": True,
                "w": "majority",
            },
        }
    }
    MIGRATION_MODULES = {
        "auth": "connectly.mongo_migrations.auth",
        "contenttypes": "connectly.mongo_migrations.contenttypes",
        "admin": "connectly.mongo_migrations.admin",
    }
else:
    DATABASES = {
        "default": dj_database_url.config(
            default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
            conn_max_age=600,
            ssl_require=not DEBUG,
        )
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "css", BASE_DIR / "js"]
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
if os.environ.get("AWS_STORAGE_BUCKET_NAME"):
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": os.environ["AWS_STORAGE_BUCKET_NAME"],
            "region_name": os.environ.get("AWS_S3_REGION_NAME", "us-east-1"),
            "endpoint_url": os.environ.get("AWS_S3_ENDPOINT_URL") or None,
            "default_acl": None,
            "file_overwrite": False,
        },
    }

DEFAULT_AUTO_FIELD = (
    "django_mongodb_backend.fields.ObjectIdAutoField"
    if MONGODB_ENABLED
    else "django.db.models.BigAutoField"
)
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "feed"
LOGOUT_REDIRECT_URL = "login"

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    if os.environ.get("RENDER"):
        SECURE_SSL_REDIRECT = True
        SECURE_HSTS_SECONDS = 31536000
        if render_hostname:
            render_origin = f"https://{render_hostname}"
            if render_origin not in CSRF_TRUSTED_ORIGINS:
                CSRF_TRUSTED_ORIGINS.append(render_origin)
