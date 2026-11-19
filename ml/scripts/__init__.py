"""Sets Django up before any script imports backend code that loads models; run the scripts with `python -m`. Spawned
workers import this package too, before re-importing the script."""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mainsite.settings")
django.setup()
