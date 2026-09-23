import datetime
import json
from io import StringIO

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.utils import timezone

from election.election_config_storage import ELECTION_CONFIGS_PREFIX
from election.tests.factories import ElectionConfigFactory


def _store_config(identifier, date):
    key = f"{ELECTION_CONFIGS_PREFIX}{identifier}.json"
    data = {"election": {"id": identifier, "date": date.replace(tzinfo=None).isoformat()}}
    default_storage.save(key, ContentFile(json.dumps(data).encode()))
    return key


@pytest.fixture
def expired_and_current_configs():
    expired_date = timezone.localtime() - datetime.timedelta(days=365)
    current_date = timezone.localtime() - datetime.timedelta(days=1)
    ElectionConfigFactory(identifier="GR2000", date=expired_date)
    ElectionConfigFactory(identifier="GR2099", date=current_date)
    return _store_config("GR2000", expired_date), _store_config("GR2099", current_date)


@pytest.mark.django_db
def test_confirm_removes_the_config_file_of_an_expired_election(expired_and_current_configs):
    expired_key, current_key = expired_and_current_configs

    out = StringIO()
    call_command("delete_expired_elections", "--confirm", stdout=out)

    assert not default_storage.exists(expired_key)
    assert default_storage.exists(current_key)
    assert expired_key in out.getvalue()


@pytest.mark.django_db
def test_dry_run_leaves_config_files_in_place(expired_and_current_configs):
    expired_key, current_key = expired_and_current_configs

    call_command("delete_expired_elections")

    assert default_storage.exists(expired_key)
    assert default_storage.exists(current_key)
