import json
import threading

import pytest
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import QuerySet

from election import election_config_importer
from election.election_config_importer import ImportInProgressError, hash_election_config_data, import_election_config
from election.models import ElectionConfig, ElectionDocument, TimelineVariant
from election.tests.factories import ElectionConfigFactory, ElectionDocumentFactory, ElectionFactory
from eml_import.models import BranchType, ImportedCommit
from eml_import.utils.github_eml_file_handler import LOCK_TIMEOUT, GithubEmlFileHandler
from region.tests.factories import RegionFactory

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
    config = import_election_config(MINIMAL_DATA)

    assert config.identifier == "TK2025"
    assert config.category == "TK"
    assert config.label == "Tweede Kamer Verkiezingen 2025"
    assert config.source_hash == hash_election_config_data(MINIMAL_DATA)
    assert config.timeline_entries.filter(variant=TimelineVariant.CSO).count() == 1
    assert config.timeline_entries.filter(variant=TimelineVariant.DSO).count() == 0
    assert config.timeline_entries.filter(variant=TimelineVariant.DEFAULT).count() == 1


@pytest.mark.django_db
def test_import_updates_an_existing_config_in_place_and_replaces_timeline_entries():
    existing = ElectionConfigFactory(identifier="TK2025", label="Old label")

    config = import_election_config(MINIMAL_DATA)

    assert config.pk == existing.pk
    assert ElectionConfig.with_expired.filter(identifier="TK2025").count() == 1
    assert config.label == "Tweede Kamer Verkiezingen 2025"
    assert config.source_hash == hash_election_config_data(MINIMAL_DATA)


@pytest.mark.django_db
def test_import_is_a_noop_for_unchanged_branches():
    existing = ElectionConfigFactory(
        identifier="TK2025",
        gh_exchange_branch="auto-tk2025-uit",
        gh_counting_results_branch="auto-tk2025-tel",
    )
    election = ElectionFactory(election_config=existing)
    ImportedCommit.objects.create(election_config=existing, branch_type=BranchType.EXCHANGE, commit_sha="abc123")

    import_election_config(MINIMAL_DATA)

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

    config = import_election_config(MINIMAL_DATA)

    assert not config.elections.filter(pk=election.pk).exists()
    assert not config.imported_commits.exists()
    assert config.gh_exchange_branch == "auto-tk2025-uit"


@pytest.mark.django_db
def test_import_hash_is_unaffected_by_formatting_only_differences():
    reformatted = json.loads(json.dumps(MINIMAL_DATA, indent=4, sort_keys=False))

    import_election_config(MINIMAL_DATA)
    config = import_election_config(reformatted)

    assert config.source_hash == hash_election_config_data(MINIMAL_DATA)


@pytest.mark.django_db
def test_import_deletes_stored_documents_when_a_github_branch_changes():
    existing = ElectionConfigFactory(
        identifier="TK2025",
        gh_exchange_branch="some-old-branch",
        gh_counting_results_branch="auto-tk2025-tel",
    )
    election = ElectionFactory(election_config=existing)
    region = RegionFactory(election=election)
    document = ElectionDocumentFactory(region=region, storage_key="TK2025/gsb/doc.xml")
    default_storage.save(document.storage_key, ContentFile(b"<xml />"))

    try:
        config = import_election_config(MINIMAL_DATA)

        assert config.gh_exchange_branch == "auto-tk2025-uit"
        assert not ElectionDocument.all_objects.filter(pk=document.pk).exists()
        assert not default_storage.exists(document.storage_key)
    finally:
        default_storage.delete(document.storage_key)


@pytest.mark.django_db(transaction=True)
def test_import_blanks_branches_before_wiping_so_a_concurrent_task_skips_the_config(monkeypatch):
    """
    The branch-blanking save() has to be visible to *other* DB connections before the wipe
    starts, not just readable within the same connection/transaction. A separate thread (with
    its own connection, like a Celery worker) is used here so the assertion actually exercises
    cross-connection visibility instead of read-your-own-writes, which would pass either way.
    """
    existing = ElectionConfigFactory(
        identifier="TK2025",
        gh_exchange_branch="some-old-branch",
        gh_counting_results_branch="auto-tk2025-tel",
    )
    ElectionFactory(election_config=existing)

    branches_seen_by_other_connection = []
    original_delete = QuerySet.delete

    def _delete_and_capture(self, *args, **kwargs):
        def _read_from_another_connection():
            from django.db import connections

            try:
                row = ElectionConfig.with_expired.using("default").get(pk=existing.pk)
                branches_seen_by_other_connection.append((row.gh_exchange_branch, row.gh_counting_results_branch))
            finally:
                connections["default"].close()

        thread = threading.Thread(target=_read_from_another_connection)
        thread.start()
        thread.join()
        return original_delete(self, *args, **kwargs)

    monkeypatch.setattr(QuerySet, "delete", _delete_and_capture)

    config = import_election_config(MINIMAL_DATA)

    assert branches_seen_by_other_connection
    assert all(branches == (None, None) for branches in branches_seen_by_other_connection)
    assert config.gh_exchange_branch == "auto-tk2025-uit"
    assert config.gh_counting_results_branch == "auto-tk2025-tel"


@pytest.mark.django_db
def test_import_leaves_the_election_alone_while_its_commits_are_being_imported(monkeypatch):
    monkeypatch.setattr(election_config_importer, "WIPE_LOCK_WAIT", 0.1)
    existing = ElectionConfigFactory(
        identifier="TK2025",
        gh_exchange_branch="some-old-branch",
        gh_counting_results_branch="auto-tk2025-tel",
    )
    election = ElectionFactory(election_config=existing)

    # Stand in for a worker that is importing a commit for this election
    with cache.lock(GithubEmlFileHandler.cache_lock_key("TK2025"), timeout=LOCK_TIMEOUT):
        with pytest.raises(ImportInProgressError):
            import_election_config(MINIMAL_DATA)

    existing.refresh_from_db()
    assert existing.elections.filter(pk=election.pk).exists()
    assert existing.gh_exchange_branch == "some-old-branch"
    assert existing.source_hash != hash_election_config_data(MINIMAL_DATA)


@pytest.mark.django_db
def test_import_releases_the_lock_after_wiping():
    ElectionConfigFactory(identifier="TK2025", gh_exchange_branch="some-old-branch")

    import_election_config(MINIMAL_DATA)

    assert cache.lock(GithubEmlFileHandler.cache_lock_key("TK2025"), blocking=False).acquire() is True
