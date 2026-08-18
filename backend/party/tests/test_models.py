import pytest
from django.db import IntegrityError

from election.tests.factories import ContestFactory, ElectionFactory
from party.models import Party
from party.tests.factories import CandidateFactory, PartyFactory


@pytest.mark.django_db
def test_party_slug_is_generated_from_registered_name():
    party = Party.objects.create(election=ElectionFactory(), registered_name="Café Île Partij")

    assert party.slug == "cafe-ile-partij"


@pytest.mark.django_db
def test_party_slug_is_not_overwritten_if_already_set():
    party = Party.objects.create(
        election=ElectionFactory(),
        registered_name="Café Île Partij",
        slug="custom-slug",
    )

    assert party.slug == "custom-slug"


@pytest.mark.django_db
def test_candidate_position_is_unique_per_contest_and_party():
    """Re-importing a corrected candidate list must not duplicate a party's list."""
    contest = ContestFactory()
    party = PartyFactory(election=contest.election)
    CandidateFactory(contest=contest, party=party, identifier=1, position=1)

    with pytest.raises(IntegrityError):
        CandidateFactory(contest=contest, party=party, identifier=1, position=1)


@pytest.mark.django_db
def test_candidate_position_may_repeat_across_parties():
    contest = ContestFactory()
    election = contest.election
    first = CandidateFactory(contest=contest, party=PartyFactory(election=election), identifier=1, position=1)
    second = CandidateFactory(contest=contest, party=PartyFactory(election=election), identifier=1, position=1)

    assert first.position == second.position
