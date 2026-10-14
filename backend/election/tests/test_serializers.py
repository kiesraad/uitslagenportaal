from datetime import timedelta

import pytest
from django.utils import timezone

from election.models import ElectionCategory, TimelineEntryStatus, TimelineVariant
from election.serializers import (
    ElectionConfigSerializer,
    ElectionDocumentSerializer,
    TimelineEntrySerializer,
)
from election.tests.factories import (
    ElectionConfigFactory,
    ElectionDocumentFactory,
    ElectionFactory,
    TimelineEntryFactory,
)
from mainsite.models import RegionCategory
from region.tests.factories import RegionFactory


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
def test_timeline_entry_serializer_nests_title_and_body_by_locale():
    entry = TimelineEntryFactory(title_nl="Titel", title_en="Title", body_nl="Tekst", body_en="Body")

    data = TimelineEntrySerializer(entry).data

    assert data["title"] == {"nl": "Titel", "en": "Title"}
    assert data["body"] == {"nl": "Tekst", "en": "Body"}


@pytest.mark.django_db
def test_timeline_entry_serializer_falls_back_to_dutch_when_english_is_blank():
    entry = TimelineEntryFactory(title_nl="Titel", title_en="", body_nl="Tekst", body_en="")

    data = TimelineEntrySerializer(entry).data

    assert data["title"] == {"nl": "Titel", "en": "Titel"}
    assert data["body"] == {"nl": "Tekst", "en": "Tekst"}


@pytest.mark.django_db
def test_election_config_serializer_includes_csb_type_without_imported_regions():
    config = ElectionConfigFactory(category=ElectionCategory.WS.value)

    data = ElectionConfigSerializer(config).data

    assert data["csb_type"] == RegionCategory.WATERSCHAP
    assert data["single_csb"] is None


@pytest.mark.django_db
def test_election_config_serializer_returns_the_single_csb():
    election = ElectionFactory(election_config=ElectionConfigFactory(category=ElectionCategory.TK.value))
    staat = RegionFactory(election=election, region_category=RegionCategory.STAAT, region_name="Nederland")
    RegionFactory(election=election, region_category=RegionCategory.KIESKRING, region_name="Amsterdam")

    data = ElectionConfigSerializer(election.election_config).data

    assert data["single_csb"] == {"region_name": "Nederland", "slug": staat.slug}


@pytest.mark.django_db
def test_election_config_serializer_has_no_single_csb_when_there_are_several():
    election = ElectionFactory(election_config=ElectionConfigFactory(category=ElectionCategory.WS.value))
    RegionFactory(election=election, region_category=RegionCategory.WATERSCHAP, region_name="Scheldestromen")
    RegionFactory(election=election, region_category=RegionCategory.WATERSCHAP, region_name="Rivierenland")

    data = ElectionConfigSerializer(election.election_config).data

    assert data["single_csb"] is None


@pytest.mark.django_db
def test_election_config_serializer_only_returns_default_variant_timeline_entries():
    config = ElectionConfigFactory()
    TimelineEntryFactory(election_config=config, variant=TimelineVariant.CSO)
    TimelineEntryFactory(election_config=config, variant=TimelineVariant.DSO)
    default_entry = TimelineEntryFactory(election_config=config, variant=TimelineVariant.DEFAULT)

    data = ElectionConfigSerializer(config).data

    titles = [entry["title"]["nl"] for entry in data["timeline_entries"]]
    assert titles == [default_entry.title_nl]


@pytest.mark.django_db
def test_election_document_serializer_url():
    document = ElectionDocumentFactory()

    data = ElectionDocumentSerializer(document).data

    assert data["url"] == f"/api/documents/{document.pk}/download/"
