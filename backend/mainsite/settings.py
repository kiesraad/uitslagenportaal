import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("SECRET_KEY", "secret")

DEBUG = os.environ.get("DEBUG", "true").strip().lower() in {"1", "true", "yes"}

ALLOWED_HOSTS = [
    host.strip() for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",") if host.strip()
]


INSTALLED_APPS = [
    "mainsite.apps.MainsiteConfig",
    "election.apps.ElectionConfig",
    "region.apps.RegionConfig",
    "party.apps.PartyConfig",
    "eml_import.apps.EmlImportConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",
    "rest_framework",
    "corsheaders",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "mainsite.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "mainsite.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": os.environ["DB_HOST"],
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

# Redis config
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")
REDIS_USER = os.environ.get("REDIS_USER", "")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")
REDIS_URL = f"redis://{REDIS_USER}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"

# Celery config - use a different broker and result backend Redis DB
CELERY_BROKER_URL = REDIS_URL + "/1"
CELERY_RESULT_BACKEND = REDIS_URL + "/2"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 0.5h

# Prefork sizes its pool from the host's CPU count, which bears no relation to what the
# worker is allowed to use, and a child never hands an EML batch's peak memory back to the
# OS. So bound the fan-out and retire a child every few tasks. Both are read between tasks,
# so neither can cut a running import short.
CELERY_WORKER_CONCURRENCY = int(os.environ.get("CELERY_WORKER_CONCURRENCY", "2"))
CELERY_WORKER_MAX_TASKS_PER_CHILD = int(os.environ.get("CELERY_WORKER_MAX_TASKS_PER_CHILD", "5"))
# An import runs for minutes, so reserving more than one message per child only leaves work
# queued behind a busy one.
CELERY_WORKER_PREFETCH_MULTIPLIER = int(os.environ.get("CELERY_WORKER_PREFETCH_MULTIPLIER", "1"))

# Cache config
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL + "/0",
    }
}

# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "en-us"

USE_TZ = True
TIME_ZONE = "Europe/Amsterdam"


STATIC_URL = "static/"

# No pagination for now
# REST_FRAMEWORK = {
#     "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
#     "PAGE_SIZE": 100,
# }

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173",
    ).split(",")
    if origin.strip()
]


# GitHub EML ingress
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_INGRESS_REPO = os.environ.get("GITHUB_INGRESS_REPO")  # "owner/repo"


# Object storage
# S3-compatible: RustFS locally (see docker-compose.yml), Scaleway in production.
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": os.environ.get("S3_BUCKET_NAME", "uitslagenportaal"),
            "endpoint_url": os.environ.get("S3_ENDPOINT_URL", "http://localhost:9000"),
            "access_key": os.environ.get("S3_ACCESS_KEY", "uitslagenportaal"),
            "secret_key": os.environ.get("S3_SECRET_KEY", "password"),
            "region_name": os.environ.get("S3_REGION", "nl-ams"),
            "custom_domain": os.environ.get("S3_PUBLIC_DOMAIN", "localhost:9000/uitslagenportaal"),
            "url_protocol": os.environ.get("S3_URL_PROTOCOL", "http:"),
            # RustFS is reached by hostname, so virtual-host style addressing
            # (bucket.object-storage:9000) would not resolve.
            "addressing_style": os.environ.get("S3_ADDRESSING_STYLE", "path"),
            # Public objects: no signature on generated URLs.
            "querystring_auth": False,
            "file_overwrite": True,
            # Makes browsers download documents instead of rendering them.
            "object_parameters": {"ContentDisposition": "attachment"},
        },
    },
    # Assigning STORAGES replaces Django's default dict, so staticfiles has to
    # be restated here or collectstatic and the admin lose their backend.
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


# Logging
# https://docs.djangoproject.com/en/6.0/topics/logging/

LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{asctime} {processName} - {levelname} - {name} - {message}",
            "style": "{",
        },
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "simple",
        },
    },
    # Handler on the root logger, so every app logger is covered without
    # having to list them here.
    "root": {
        "handlers": ["stdout"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        # Set some loggers to INFO to prevent spam if LOG_LEVEL is DEBUG
        "django": {"level": "INFO"},
        "boto3": {"level": "INFO"},
        "botocore": {"level": "INFO"},
        "s3transfer": {"level": "INFO"},
        "urllib3": {"level": "INFO"},
        "celery": {"level": "INFO"},
        "kombu": {"level": "INFO"},
        "redis.connection": {"level": "INFO"},
    },
}
