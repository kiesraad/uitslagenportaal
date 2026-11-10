import pytest
from django.db import DatabaseError, InterfaceError

from mainsite import views


@pytest.mark.django_db
def test_healthz_reports_ok(client):
    response = client.get("/healthz/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# InterfaceError is not a DatabaseError, so the two arrive by different routes: psycopg
# raises it for a connection that has already been closed.
@pytest.mark.django_db
@pytest.mark.parametrize("error", [DatabaseError, InterfaceError])
def test_healthz_reports_unhealthy_when_the_database_is_unreachable(client, monkeypatch, error):
    def refuse_connection():
        raise error("connection refused")

    monkeypatch.setattr(views.connection, "cursor", refuse_connection)

    response = client.get("/healthz/")

    assert response.status_code == 503
    assert response.json() == {"status": "unhealthy"}


@pytest.mark.django_db
def test_metrics_endpoint_serves_prometheus_exposition(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    # The metric names depend on what has been exercised in the process; the exposition
    # format itself is what this asserts on.
    assert b"# HELP" in response.content
