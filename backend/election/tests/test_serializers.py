from datetime import UTC, datetime

import pytest

from election.models import ElectionCategory, TimelineDateQualifier, TimelineEvent
from election.serializers import (
    ElectionConfigSerializer,
    ElectionDocumentSerializer,
    TimelineDateSerializer,
)
from election.tests.factories import (
    ElectionConfigFactory,
    ElectionDocumentFactory,
    ElectionFactory,
    TimelineDateFactory,
)
from mainsite.models import RegionCategory
from region.tests.factories import RegionFactory


@pytest.mark.django_db
def test_timeline_date_serializer_returns_event_date_and_qualifier():
    timeline_date = TimelineDateFactory(
        event=TimelineEvent.CSB_CHECK,
        date=datetime(2026, 9, 26, 9, 0, tzinfo=UTC),
        qualifier=TimelineDateQualifier.FROM,
    )

    data = TimelineDateSerializer(timeline_date).data

    assert data == {"event": "csb_check", "date": "2026-09-26T11:00:00+02:00", "qualifier": "from"}


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
def test_election_config_serializer_has_no_single_csb_when_only_one_waterschap_is_imported():
    election = ElectionFactory(election_config=ElectionConfigFactory(category=ElectionCategory.WS.value))
    RegionFactory(election=election, region_category=RegionCategory.WATERSCHAP, region_name="Scheldestromen")

    data = ElectionConfigSerializer(election.election_config).data

    assert data["single_csb"] is None


@pytest.mark.django_db
def test_election_config_serializer_returns_its_own_timeline_dates():
    config = ElectionConfigFactory()
    TimelineDateFactory(election_config=config, event=TimelineEvent.SB_VOTE_COUNT)
    TimelineDateFactory(election_config=config, event=TimelineEvent.CSB_RESULT_PUBLISH)
    TimelineDateFactory(event=TimelineEvent.CSB_CHECK)

    data = ElectionConfigSerializer(config).data

    events = {timeline_date["event"] for timeline_date in data["timeline_dates"]}
    assert events == {TimelineEvent.SB_VOTE_COUNT, TimelineEvent.CSB_RESULT_PUBLISH}


@pytest.mark.django_db
def test_election_document_serializer_url():
    document = ElectionDocumentFactory()

    data = ElectionDocumentSerializer(document).data

    assert data["url"] == f"/api/documents/{document.pk}/download/"
