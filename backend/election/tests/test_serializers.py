from datetime import timedelta

import pytest
from django.test import RequestFactory
from django.utils import timezone

from election.models import (
    ElectionConfig,
    ElectionDocument,
    TimelineEntry,
    TimelineEntryStatus,
    TimelineVariant,
)
from election.serializers import (
    ElectionConfigSerializer,
    ElectionDocumentSerializer,
    TimelineEntrySerializer,
)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("offset_days", "expected_status"),
    [
        (-2, TimelineEntryStatus.DONE),
        (0, TimelineEntryStatus.IN_PROGRESS),
        (2, TimelineEntryStatus.PENDING),
    ],
)
def test_timeline_entry_serializer_status(offset_days, expected_status):
    config = ElectionConfig.objects.create(
        identifier="AB2023",
        category="AB",
        date="2023-03-15T00:00:00Z",
    )
    entry = TimelineEntry.objects.create(
        election_config=config,
        status="pending",
        title="Some entry",
        date=timezone.now() + timedelta(days=offset_days),
        body="",
    )

    data = TimelineEntrySerializer(entry).data

    assert data["status"] == expected_status


@pytest.mark.django_db
def test_election_config_serializer_only_returns_default_variant_timeline_entries():
    config = ElectionConfig.objects.create(
        identifier="AB2023",
        category="AB",
        date="2023-03-15T00:00:00Z",
    )
    TimelineEntry.objects.create(
        election_config=config,
        variant=TimelineVariant.CSO,
        status="pending",
        title="CSO entry",
        date=timezone.now(),
        body="",
    )
    TimelineEntry.objects.create(
        election_config=config,
        variant=TimelineVariant.DSO,
        status="pending",
        title="DSO entry",
        date=timezone.now(),
        body="",
    )
    default_entry = TimelineEntry.objects.create(
        election_config=config,
        variant=TimelineVariant.DEFAULT,
        status="pending",
        title="Default entry",
        date=timezone.now(),
        body="",
    )

    data = ElectionConfigSerializer(config).data

    titles = [entry["title"] for entry in data["timeline_entries"]]
    assert titles == [default_entry.title]


@pytest.mark.django_db
def test_election_document_serializer_url_is_absolute_with_request_context():
    document = ElectionDocument.objects.create(
        storage_key="some/document.xml",
        size=123,
    )
    request = RequestFactory().get("/")

    data = ElectionDocumentSerializer(document, context={"request": request}).data

    assert data["url"] == f"http://testserver/api/documents/{document.pk}/download/"


@pytest.mark.django_db
def test_election_document_serializer_url_is_relative_path_without_request_context():
    document = ElectionDocument.objects.create(
        storage_key="some/document.xml",
        size=123,
    )

    data = ElectionDocumentSerializer(document).data

    assert data["url"] == f"/api/documents/{document.pk}/download/"
