from datetime import timedelta

import pytest
from django.test import RequestFactory
from django.utils import timezone

from election.models import TimelineEntryStatus, TimelineVariant
from election.serializers import (
    ElectionConfigSerializer,
    ElectionDocumentSerializer,
    TimelineEntrySerializer,
)
from election.tests.factories import ElectionConfigFactory, ElectionDocumentFactory, TimelineEntryFactory


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
    entry = TimelineEntryFactory(date=timezone.now() + timedelta(days=offset_days))

    data = TimelineEntrySerializer(entry).data

    assert data["status"] == expected_status


@pytest.mark.django_db
def test_election_config_serializer_only_returns_default_variant_timeline_entries():
    config = ElectionConfigFactory()
    TimelineEntryFactory(election_config=config, variant=TimelineVariant.CSO)
    TimelineEntryFactory(election_config=config, variant=TimelineVariant.DSO)
    default_entry = TimelineEntryFactory(election_config=config, variant=TimelineVariant.DEFAULT)

    data = ElectionConfigSerializer(config).data

    titles = [entry["title"] for entry in data["timeline_entries"]]
    assert titles == [default_entry.title]


@pytest.mark.django_db
def test_election_document_serializer_url():
    document = ElectionDocumentFactory()

    data = ElectionDocumentSerializer(document).data

    assert data["url"] == f"/api/documents/{document.pk}/download/"
