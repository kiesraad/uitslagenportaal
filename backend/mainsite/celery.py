import copy
import logging.config
import os

from celery import Celery
from celery.signals import setup_logging

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mainsite.settings")

app = Celery()

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@setup_logging.connect
def configure_logging(**_):
    """
    Log the same way Django does, instead of using Celery's own logging setup.

    Connecting to this signal at all is what stops Celery from hijacking the
    root logger; we then apply Django's LOGGING ourselves.
    """
    from django.conf import settings

    config = copy.deepcopy(settings.LOGGING)
    config["handlers"]["stdout"]["formatter"] = "simple"
    logging.config.dictConfig(config)

