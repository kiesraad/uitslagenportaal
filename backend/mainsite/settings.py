import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("SECRET_KEY", "secret")

DEBUG = True

ALLOWED_HOSTS = []


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
# S3-compatible: MinIO locally (see docker-compose.yml), Scaleway in production.
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
            # MinIO is reached by hostname, so virtual-host style addressing
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
            "format": "{asctime} {levelname:8} {name}: {message}",
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
        # Keep Django itself at INFO even when our own code runs at DEBUG,
        # otherwise every SQL query gets logged.
        "django": {"level": "INFO"},
        # Same for the AWS SDK, which logs every endpoint lookup, signature and header at DEBUG
        "boto3": {"level": "INFO"},
        "botocore": {"level": "INFO"},
        "s3transfer": {"level": "INFO"},
        "urllib3": {"level": "INFO"},
    },
}
