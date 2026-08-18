import pytest
from django_redis.pool import ConnectionFactory
from fakeredis import FakeRedisConnection, FakeServer


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


@pytest.fixture(autouse=True)
def fake_redis_cache(settings):
    """
    Back the cache with an in-process fake Redis.

    Each test gets its own FakeServer. django_redis caches connection pools in a
    process-global dict keyed on the URL, so that dict has to be cleared as well;
    otherwise every test after the first keeps using the first test's server.
    """
    ConnectionFactory._pools.clear()
    settings.CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            # Deliberately not REDIS_URL, so this can never share a pool with the real server
            "LOCATION": "redis://fake:6379/0",
            "OPTIONS": {
                "CONNECTION_POOL_KWARGS": {
                    "connection_class": FakeRedisConnection,
                    "server": FakeServer(),
                },
            },
        }
    }
    yield
    ConnectionFactory._pools.clear()
