import pytest


@pytest.fixture(autouse=True)
def in_memory_storage(settings):
    """
    Keep tests off the real object storage.

    STORAGES points at an S3-compatible bucket, so without this any test that
    touches default_storage would read and write actual objects. Overriding it
    for every test makes that impossible by default rather than by convention.
    """
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
