import pytest
from django.core.management import CommandError, call_command

from election.models import ElectionConfig
from election.tests.factories import ElectionConfigFactory, ElectionFactory
from eml_import.tests.factories import ImportedCommitFactory


@pytest.mark.django_db
def test_wipes_elections_and_imported_commits_but_keeps_the_config():
    config = ElectionConfigFactory(
        identifier="GR2026",
        gh_exchange_branch="auto-gr2026-uit",
        gh_counting_results_branch="auto-gr2026-tel",
    )
    ElectionFactory(election_config=config)
    ImportedCommitFactory(election_config=config)

    call_command("wipe_election_data", "GR2026")

    config = ElectionConfig.with_expired.get(identifier="GR2026")
    assert not config.elections.exists()
    assert not config.imported_commits.exists()
    assert (config.gh_exchange_branch, config.gh_counting_results_branch) == ("auto-gr2026-uit", "auto-gr2026-tel")


@pytest.mark.django_db
def test_leaves_other_configs_alone():
    ElectionConfigFactory(identifier="GR2026")
    other = ElectionConfigFactory(identifier="PS2027")
    election = ElectionFactory(election_config=other)

    call_command("wipe_election_data", "GR2026")

    assert other.elections.filter(pk=election.pk).exists()


@pytest.mark.django_db
def test_raises_for_an_unknown_config():
    with pytest.raises(CommandError, match="GR2026"):
        call_command("wipe_election_data", "GR2026")
