import pytest

from election.election_config_importer import import_election_config
from election.models import ElectionConfig, TimelineVariant
from election.tests.factories import ElectionConfigFactory, ElectionFactory
from eml_import.models import BranchType, ImportedCommit

MINIMAL_DATA = {
    "election": {
        "id": "TK2025",
        "label": "Tweede Kamer Verkiezingen 2025",
        "category": "TK",
        "date": "2025-04-12T10:00:00",
        "issue_report_opens_at": "2025-08-18T11:00:00",
        "issue_report_deadline": "2025-09-12T10:00:00",
        "gh_counting_results_branch": "auto-tk2025-tel",
        "gh_exchange_branch": "auto-tk2025-uit",
    },
    "timeline_entries_cso": [
        {
            "title": {"nl": "CSO titel", "en": "CSO title"},
            "date": "2025-12-15T11:00:00",
            "body": {"nl": "CSO body", "en": "CSO body"},
        }
    ],
    "timeline_entries_dso": [],
    "timeline_entries_default": [
        {
            "title": {"nl": "Default titel", "en": "Default title"},
            "date": "2025-12-15T11:00:00",
            "body": {"nl": "Default body", "en": "Default body"},
        }
    ],
}


@pytest.mark.django_db
def test_import_creates_a_new_election_config_with_its_timeline_entries():
    config = import_election_config(MINIMAL_DATA, source_hash="hash-1")

    assert config.identifier == "TK2025"
    assert config.category == "TK"
    assert config.label == "Tweede Kamer Verkiezingen 2025"
    assert config.source_hash == "hash-1"
    assert config.timeline_entries.filter(variant=TimelineVariant.CSO).count() == 1
    assert config.timeline_entries.filter(variant=TimelineVariant.DSO).count() == 0
    assert config.timeline_entries.filter(variant=TimelineVariant.DEFAULT).count() == 1


@pytest.mark.django_db
def test_import_updates_an_existing_config_in_place_and_replaces_timeline_entries():
    existing = ElectionConfigFactory(identifier="TK2025", label="Old label")

    config = import_election_config(MINIMAL_DATA, source_hash="hash-2")

    assert config.pk == existing.pk
    assert ElectionConfig.with_expired.filter(identifier="TK2025").count() == 1
    assert config.label == "Tweede Kamer Verkiezingen 2025"
    assert config.source_hash == "hash-2"


@pytest.mark.django_db
def test_import_is_a_noop_for_unchanged_branches():
    existing = ElectionConfigFactory(
        identifier="TK2025",
        gh_exchange_branch="auto-tk2025-uit",
        gh_counting_results_branch="auto-tk2025-tel",
    )
    election = ElectionFactory(election_config=existing)
    ImportedCommit.objects.create(election_config=existing, branch_type=BranchType.EXCHANGE, commit_sha="abc123")

    import_election_config(MINIMAL_DATA, source_hash="hash-3")

    assert existing.elections.filter(pk=election.pk).exists()
    assert existing.imported_commits.exists()


@pytest.mark.django_db
def test_import_wipes_election_data_when_a_github_branch_changes():
    existing = ElectionConfigFactory(
        identifier="TK2025",
        gh_exchange_branch="some-old-branch",
        gh_counting_results_branch="auto-tk2025-tel",
    )
    election = ElectionFactory(election_config=existing)
    ImportedCommit.objects.create(election_config=existing, branch_type=BranchType.EXCHANGE, commit_sha="abc123")

    config = import_election_config(MINIMAL_DATA, source_hash="hash-4")

    assert not config.elections.filter(pk=election.pk).exists()
    assert not config.imported_commits.exists()
    assert config.gh_exchange_branch == "auto-tk2025-uit"


@pytest.mark.django_db
def test_import_leaves_source_hash_null_when_not_given():
    import_election_config(MINIMAL_DATA)

    assert ElectionConfig.with_expired.get(identifier="TK2025").source_hash is None
