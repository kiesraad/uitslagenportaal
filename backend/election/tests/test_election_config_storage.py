import json

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from election import election_config_storage
from election.election_config_storage import (
    ELECTION_CONFIGS_PREFIX,
    import_new_election_configs,
    remove_expired_election_configs,
)
from election.models import ElectionConfig
from election.tests.factories import ElectionConfigFactory
from election.utils import tz_aware_from_isoformat

MINIMAL_DATA = {
    "election": {
        "id": "AB2099",
        "label": "Test election",
        "category": "WS",
        "date": "2099-04-12T10:00:00",
        "issue_report_opens_at": "2099-08-18T11:00:00",
        "issue_report_deadline": "2099-09-12T10:00:00",
    },
    "timeline_entries_cso": [],
    "timeline_entries_dso": [],
    "timeline_entries_default": [],
}

EXPIRED_DATA = {**MINIMAL_DATA, "election": {**MINIMAL_DATA["election"], "date": "2000-04-12T10:00:00"}}


@pytest.fixture
def uploaded_config():
    """Uploads AB2099.json and cleans it up afterwards so the bucket stays tidy."""
    key = f"{ELECTION_CONFIGS_PREFIX}AB2099.json"

    def _upload(data=MINIMAL_DATA):
        default_storage.delete(key)
        default_storage.save(key, ContentFile(json.dumps(data).encode()))
        return key

    yield _upload
    default_storage.delete(key)


@pytest.mark.django_db
def test_import_new_election_configs_imports_a_new_file(uploaded_config):
    uploaded_config()

    imported = import_new_election_configs()

    assert imported == 1
    config = ElectionConfig.with_expired.get(identifier="AB2099")
    assert config.label == "Test election"
    assert config.source_hash


@pytest.mark.django_db
def test_import_new_election_configs_skips_unchanged_files(uploaded_config):
    uploaded_config()
    import_new_election_configs()

    imported = import_new_election_configs()

    assert imported == 0


@pytest.mark.django_db
def test_import_new_election_configs_reimports_a_changed_file(uploaded_config):
    uploaded_config()
    import_new_election_configs()

    changed = {**MINIMAL_DATA, "election": {**MINIMAL_DATA["election"], "label": "Updated label"}}
    uploaded_config(changed)
    imported = import_new_election_configs()

    assert imported == 1
    assert ElectionConfig.with_expired.get(identifier="AB2099").label == "Updated label"


@pytest.mark.django_db
def test_import_new_election_configs_skips_a_reformatted_but_unchanged_file(uploaded_config):
    key = f"{ELECTION_CONFIGS_PREFIX}AB2099.json"
    default_storage.delete(key)
    default_storage.save(key, ContentFile(json.dumps(MINIMAL_DATA).encode()))
    import_new_election_configs()

    # Same data, different formatting: indentation and key order both changed.
    default_storage.delete(key)
    default_storage.save(key, ContentFile(json.dumps(MINIMAL_DATA, indent=4, sort_keys=True).encode()))
    imported = import_new_election_configs()

    assert imported == 0


@pytest.mark.django_db
def test_import_new_election_configs_ignores_non_json_files():
    key = f"{ELECTION_CONFIGS_PREFIX}readme.txt"
    default_storage.save(key, ContentFile(b"not a config"))

    try:
        imported = import_new_election_configs()
    finally:
        default_storage.delete(key)

    assert imported == 0


@pytest.mark.django_db
def test_import_new_election_configs_skips_and_continues_on_invalid_json():
    key = f"{ELECTION_CONFIGS_PREFIX}broken.json"
    default_storage.save(key, ContentFile(b"{not valid json"))

    try:
        imported = import_new_election_configs()
    finally:
        default_storage.delete(key)

    assert imported == 0


@pytest.mark.django_db
def test_import_new_election_configs_dedupes_on_the_id_the_file_declares_not_the_file_name():
    # The file is named after a different id than the one its body declares.
    key = f"{ELECTION_CONFIGS_PREFIX}mismatched-name.json"
    default_storage.save(key, ContentFile(json.dumps(MINIMAL_DATA).encode()))

    try:
        first = import_new_election_configs()
        second = import_new_election_configs()
    finally:
        default_storage.delete(key)
        ElectionConfig.with_expired.filter(identifier="AB2099").delete()

    assert first == 1
    # A dedup keyed on the file name would never match this row and re-import forever.
    assert second == 0


@pytest.mark.django_db
def test_import_new_election_configs_does_not_affect_seeded_configs_without_a_hash():
    ElectionConfigFactory(identifier="AB2099")

    import_new_election_configs()

    # Without an uploaded file, nothing in storage matches; the seeded row is untouched.
    assert ElectionConfig.with_expired.get(identifier="AB2099").source_hash is None


@pytest.mark.django_db
def test_import_new_election_configs_skips_an_expired_election(uploaded_config):
    uploaded_config(EXPIRED_DATA)

    imported = import_new_election_configs()

    assert imported == 0
    assert not ElectionConfig.with_expired.filter(identifier="AB2099").exists()


@pytest.mark.django_db
def test_import_new_election_configs_imports_an_election_on_the_visibility_cutoff(uploaded_config, monkeypatch):
    election_date = tz_aware_from_isoformat(MINIMAL_DATA["election"]["date"])
    monkeypatch.setattr(election_config_storage, "visibility_cutoff", lambda: election_date)
    uploaded_config()

    imported = import_new_election_configs()

    assert imported == 1


def _store(filename, data):
    key = f"{ELECTION_CONFIGS_PREFIX}{filename}"
    default_storage.save(key, ContentFile(json.dumps(data).encode()))
    return key


def test_remove_expired_election_configs_deletes_expired_listed_configs():
    first = _store("random-name.json", EXPIRED_DATA)
    second = _store("CD2000.json", {**EXPIRED_DATA, "election": {**EXPIRED_DATA["election"], "id": "CD2000"}})

    # Keep if not listed
    assert remove_expired_election_configs(["XY2000"]) == []
    assert default_storage.exists(first)
    assert default_storage.exists(second)

    # Remove if listed based on identifier in the data
    deleted = remove_expired_election_configs(["AB2099", "CD2000"])

    assert sorted(deleted) == sorted([first, second])
    assert not default_storage.exists(first)
    assert not default_storage.exists(second)


def test_remove_expired_election_configs_keeps_a_listed_config_that_is_not_expired():
    key = _store("AB2099.json", MINIMAL_DATA)

    assert remove_expired_election_configs(["AB2099"]) == []
    assert default_storage.exists(key)


def test_remove_expired_election_configs_skips_invalid_and_non_json_files_and_continues():
    broken = f"{ELECTION_CONFIGS_PREFIX}broken.json"
    default_storage.save(broken, ContentFile(b"{not valid json"))
    readme = f"{ELECTION_CONFIGS_PREFIX}readme.txt"
    default_storage.save(readme, ContentFile(b"not a config"))
    expired = _store("AB2099.json", EXPIRED_DATA)

    deleted = remove_expired_election_configs(["AB2099"])

    assert deleted == [expired]
    assert default_storage.exists(broken)
    assert default_storage.exists(readme)
    assert not default_storage.exists(expired)


def test_remove_expired_election_configs_is_a_noop_without_a_configs_folder():
    assert remove_expired_election_configs(["AB2099"]) == []
