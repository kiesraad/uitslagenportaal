from datetime import timedelta
from unittest.mock import ANY, call, create_autospec, patch

import pytest
from celery import Celery
from celery.schedules import crontab
from requests import RequestException

from election.tests.factories import ElectionConfigFactory
from election.utils import visibility_cutoff
from eml_import import tasks
from eml_import.tasks import import_election_eml_commits, import_next_eml_commits, setup_periodic_tasks


@pytest.mark.django_db
@patch.object(tasks.import_election_eml_commits, "delay")
def test_fan_out_task_queues_one_import_per_visible_election_config(delay):
    current = ElectionConfigFactory()
    ElectionConfigFactory(date=visibility_cutoff() - timedelta(days=1))

    import_next_eml_commits()

    # A task per election, so a failing election retries on its own instead of taking the others
    # with it. Elections past their visibility cutoff are hidden by the default manager.
    assert delay.call_args_list == [call(current.id)]


@pytest.mark.django_db
@patch.object(tasks, "GithubEmlImporter", autospec=True)
def test_import_task_imports_the_election_config_it_was_queued_for(github_eml_importer):
    election_config = ElectionConfigFactory()
    ElectionConfigFactory()

    import_election_eml_commits(election_config.id)

    github_eml_importer.assert_called_once_with(election_config)
    github_eml_importer.return_value.run.assert_called_once_with()


@pytest.mark.django_db
@patch.object(tasks, "GithubEmlImporter", autospec=True)
def test_import_task_lets_importer_failures_escape_so_celery_can_retry(github_eml_importer):
    election_config = ElectionConfigFactory()
    github_eml_importer.return_value.run.side_effect = RequestException("GitHub is unreachable")

    # Swallowing this would leave the election silently stuck until the next beat tick
    with pytest.raises(RequestException):
        import_election_eml_commits(election_config.id)


def test_setup_periodic_tasks_schedules_the_import_every_ten_minutes():
    sender = create_autospec(Celery, instance=True)

    setup_periodic_tasks(sender)

    # The name only shows up in beat's logs, so it is not worth pinning
    sender.add_periodic_task.assert_called_once_with(crontab(minute="*/10"), import_next_eml_commits.s(), name=ANY)
