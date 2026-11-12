import datetime

import pytest
from django.utils import timezone

from election.eml_dates import election_config_eml_dates, region_eml_dates
from election.models import ElectionCategory, ElectionDocument
from election.tests.factories import ElectionConfigFactory, ElectionDocumentFactory, ElectionFactory
from mainsite.models import RegionCategory
from region.tests.factories import RegionFactory

FileType = ElectionDocument.FileType


def at(day: int, hour: int = 12) -> datetime.datetime:
    return timezone.make_aware(datetime.datetime(2025, 10, day, hour))


@pytest.fixture
def tree():
    """A TK with two kieskringen, each with one gemeente, and a stembureau in the first."""
    election = ElectionFactory(
        election_config=ElectionConfigFactory(category=ElectionCategory.TK.value), date=datetime.date(2025, 10, 29)
    )
    csb = RegionFactory(election=election, region_category=RegionCategory.STAAT)
    kieskringen = [
        RegionFactory(election=election, region_category=RegionCategory.KIESKRING, parent=csb, csb=csb)
        for _ in range(2)
    ]
    gemeenten = [
        RegionFactory(election=election, region_category=RegionCategory.GEMEENTE, parent=kieskring, csb=csb)
        for kieskring in kieskringen
    ]
    stembureau = RegionFactory(
        election=election, region_category=RegionCategory.STEMBUREAU, parent=gemeenten[0], csb=csb
    )
    return {"csb": csb, "kieskringen": kieskringen, "gemeenten": gemeenten, "stembureau": stembureau}


def eml(region, file_type, created_at, **kwargs):
    return ElectionDocumentFactory(region=region, file_type=file_type, eml_created_at=created_at, **kwargs)


@pytest.mark.django_db
def test_nothing_is_known_before_any_eml(tree):
    for region in [tree["stembureau"], tree["gemeenten"][0], tree["kieskringen"][0], tree["csb"]]:
        assert set(region_eml_dates(region).values()) == {None}


@pytest.mark.django_db
def test_a_stembureau_page_has_the_dates_of_its_gemeente_kieskring_and_csb(tree):
    gemeente, kieskring, csb = tree["gemeenten"][0], tree["kieskringen"][0], tree["csb"]
    eml(gemeente, FileType.EML_510B, at(30), is_current=False)
    eml(gemeente, FileType.EML_510B, at(31))  # a corrigendum does not move the step
    eml(kieskring, FileType.EML_510C, at(31, 15))
    eml(csb, FileType.EML_520, at(31, 18))

    assert region_eml_dates(tree["stembureau"]) == {
        "sb_vote_count": datetime.date(2025, 10, 29),
        "municipality_vote_count": at(30),
        "electoral_district_vote_count": at(31, 15),
        "csb_result_publish": at(31, 18),
    }


@pytest.mark.django_db
def test_a_step_over_several_regions_is_done_once_the_last_one_is_in(tree):
    first, second = tree["gemeenten"]
    eml(first, FileType.EML_510B, at(30))

    assert region_eml_dates(tree["csb"])["municipality_vote_count"] is None
    assert region_eml_dates(tree["csb"])["sb_vote_count"] == datetime.date(2025, 10, 29)

    eml(second, FileType.EML_510B, at(31))

    assert region_eml_dates(tree["csb"])["municipality_vote_count"] == at(31)
    assert region_eml_dates(tree["kieskringen"][0])["municipality_vote_count"] == at(30)


@pytest.mark.django_db
def test_the_general_timeline_covers_the_whole_election(tree):
    for gemeente in tree["gemeenten"]:
        eml(gemeente, FileType.EML_510B, at(30))
    for day, kieskring in enumerate(tree["kieskringen"], start=30):
        eml(kieskring, FileType.EML_510C, at(day))

    dates = election_config_eml_dates(tree["csb"].election.election_config)

    assert dates["municipality_vote_count"] == at(30)
    assert dates["electoral_district_vote_count"] == at(31)
    assert dates["csb_result_publish"] is None
