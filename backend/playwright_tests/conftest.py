"""Fixtures for the Playwright suite."""

import os
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import OperationalError, connections
from django.test import override_settings

BACKEND_ROOT = Path(__file__).resolve().parents[1]

EML_FIXTURES = BACKEND_ROOT / "mainsite" / "tests" / "fixtures" / "eml"

# Defaults are pinned by docker-compose.playwright.yml; the daily stack keeps 8080/5433/9000.
# CI has no compose stack — its service containers listen on the standard ports, so it
# overrides these from the environment (see .github/workflows/playwright.yml).
DEFAULT_BASE_URL = "http://localhost:8081"
STACK_DB_HOST = os.environ.get("PLAYWRIGHT_DB_HOST", "127.0.0.1")
STACK_DB_PORT = os.environ.get("PLAYWRIGHT_DB_PORT", "5434")
# use ip for faster connection times
STACK_S3_ENDPOINT_URL = os.environ.get("PLAYWRIGHT_S3_ENDPOINT_URL", "http://127.0.0.1:19000")

START_STACK_HINT = """
  docker compose -f docker-compose.yml -f docker-compose.playwright.yml up -d --wait
"""


@pytest.fixture(scope="session")
def base_url(request: pytest.FixtureRequest) -> str:
    """Resolve --base-url, then PLAYWRIGHT_BASE_URL, then the throwaway stack's port."""
    return request.config.getoption("--base-url") or os.environ.get("PLAYWRIGHT_BASE_URL") or DEFAULT_BASE_URL


@pytest.fixture(scope="session", autouse=True)
def require_running_stack(base_url: str) -> None:
    """Wait for the app, so a stack that is not up costs one answer, not a timeout per test."""
    try:
        urllib.request.urlopen(base_url, timeout=5).close()
        return
    except (OSError, urllib.error.URLError) as exc:
        pytest.exit(
            f"No app answering at {base_url} after 5s. Make sure it's started with:{START_STACK_HINT}({exc})",
            returncode=1,
        )


@pytest.fixture(scope="session")
def django_db_setup() -> None:
    """Overridden to a no-op: this suite shares the stack's database, and pytest-django
    would otherwise swap the connection to a test one the browser cannot see."""


@pytest.fixture(scope="session", autouse=True)
def stack_services() -> Iterator[None]:
    """
    Point this process at the throwaway stack rather than the daily one backend/.env names.

    DATABASES has to be edited through the connection, which override_settings refuses;
    STORAGES does not, and has to move too because the import writes documents.
    """
    # pytest-playwright keeps an event loop on this thread; the seeding is meant to block.
    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "1"

    connection = connections["default"]
    connection.close()
    connection.settings_dict["HOST"] = STACK_DB_HOST
    connection.settings_dict["PORT"] = STACK_DB_PORT

    storage = settings.STORAGES["default"]
    storages = {
        **settings.STORAGES,
        "default": {**storage, "OPTIONS": {**storage["OPTIONS"], "endpoint_url": STACK_S3_ENDPOINT_URL}},
    }
    with override_settings(STORAGES=storages):
        yield


@pytest.fixture(scope="session", autouse=True)
def migrated_database(django_db_blocker, stack_services: None) -> None:
    """Migrate once per run â and, being the first query, answer for an unreachable database."""
    try:
        with django_db_blocker.unblock():
            call_command("migrate", verbosity=0)
    except OperationalError as exc:
        pytest.exit(
            f"No database answering on {STACK_DB_HOST}:{STACK_DB_PORT}. Start the stack with:{START_STACK_HINT}({exc})",
            returncode=1,
        )


@pytest.fixture(scope="module", autouse=True)
def seeded_database(django_db_blocker, require_running_stack: None, migrated_database: None) -> Iterator[None]:
    """
    Wipe, seed, and import the EML fixtures around every test module.

    unblock() rather than the `db` fixture, whose transaction the stack could never see.
    workers=1 is not tuning: the importer's pool spawns interpreters that would re-import
    the test session and read backend/.env, so they would write to the daily stack.
    """
    with django_db_blocker.unblock():
        call_command("reset_and_import", str(EML_FIXTURES), workers=1)
    yield
    with django_db_blocker.unblock():
        call_command("wipe_db")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict, base_url: str) -> dict:
    """Pin the interface language: the specs assert on Dutch text."""
    return {
        **browser_context_args,
        "storage_state": {
            "cookies": [],
            "origins": [{"origin": base_url, "localStorage": [{"name": "lang", "value": "nl"}]}],
        },
    }
