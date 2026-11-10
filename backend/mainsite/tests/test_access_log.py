import json
import logging
import logging.config

import pytest
from django.conf import settings
from django.db import DatabaseError

from mainsite import views


def access_records(caplog):
    return [record for record in caplog.records if record.name == "mainsite.access"]


def test_request_is_logged_with_its_fields(client, caplog):
    with caplog.at_level(logging.INFO, logger="mainsite.access"):
        client.get("/api/does-not-exist/?page=2")

    [record] = access_records(caplog)
    assert record.method == "GET"
    assert record.path == "/api/does-not-exist/?page=2"
    assert record.status == 404
    assert record.levelno == logging.WARNING
    assert record.duration_ms >= 0


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/healthz/", "/metrics"])
def test_successful_probe_and_scrape_are_not_logged(client, caplog, path):
    with caplog.at_level(logging.INFO, logger="mainsite.access"):
        response = client.get(path)

    assert response.status_code == 200
    assert access_records(caplog) == []


@pytest.mark.django_db
def test_failing_probe_is_logged(client, caplog, monkeypatch):
    def refuse_connection():
        raise DatabaseError("connection refused")

    monkeypatch.setattr(views.connection, "cursor", refuse_connection)

    with caplog.at_level(logging.INFO, logger="mainsite.access"):
        client.get("/healthz/")

    [record] = access_records(caplog)
    assert record.status == 503
    assert record.levelno == logging.ERROR


def test_json_formatter_puts_extra_fields_in_the_object():
    config = logging.config.DictConfigurator(settings.LOGGING)
    formatter = config.configure_formatter(dict(settings.LOGGING["formatters"]["json"]))
    record = logging.makeLogRecord({"name": "mainsite.access", "levelname": "INFO", "msg": "GET / 200", "status": 200})

    line = json.loads(formatter.format(record))

    assert line["message"] == "GET / 200"
    assert line["levelname"] == "INFO"
    assert line["status"] == 200
