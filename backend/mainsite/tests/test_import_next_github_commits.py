import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from election.tests.factories import ElectionConfigFactory
from mainsite.management.commands import import_next_github_commits


@pytest.fixture
def imported_configs(monkeypatch):
    """Capture which election config the command hands to the importer."""
    configs = []

    class RecordingImporter:
        def __init__(self, election_config):
            configs.append(election_config)

        def run(self):
            return 3

    monkeypatch.setattr(import_next_github_commits, "GithubEmlFileHandler", RecordingImporter)
    return configs


@pytest.mark.django_db
def test_command_imports_the_given_election_config(imported_configs):
    election_config = ElectionConfigFactory(identifier="GR2026")

    call_command("import_next_github_commits", "GR2026")

    assert imported_configs == [election_config]


@pytest.mark.django_db
def test_command_fails_on_an_unknown_election_config(imported_configs):
    with pytest.raises(CommandError, match="GR2026"):
        call_command("import_next_github_commits", "GR2026")

    assert imported_configs == []
