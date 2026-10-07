from datetime import timedelta
from unittest.mock import ANY, call, create_autospec, patch

import pytest
from celery import Celery
from celery.schedules import crontab
from redis.exceptions import ConnectionError as RedisConnectionError
from requests import RequestException

from election.tests.factories import ElectionConfigFactory
from election.utils import visibility_cutoff
from eml_import import tasks
from eml_import.tasks import import_election_eml_commits, import_next_eml_commits, import_pvs, setup_periodic_tasks
from region.tasks import build_polling_station_pv_zip


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
@patch.object(tasks, "GithubEmlFileHandler", autospec=True)
def test_import_task_imports_the_election_config_it_was_queued_for(github_eml_file_handler):
    election_config = ElectionConfigFactory()
    ElectionConfigFactory()
    github_eml_file_handler.return_value.run.return_value = (0, False)

    import_election_eml_commits(election_config.id)

    github_eml_file_handler.assert_called_once_with(election_config)
    github_eml_file_handler.return_value.run.assert_called_once_with()


@pytest.mark.django_db
@patch.object(tasks.import_election_eml_commits, "apply_async")
@patch.object(tasks, "GithubEmlFileHandler", autospec=True)
def test_import_task_queues_a_follow_up_while_commits_remain(github_eml_file_handler, apply_async):
    election_config = ElectionConfigFactory()
    github_eml_file_handler.return_value.run.return_value = (1, True)

    import_election_eml_commits(election_config.id)

    apply_async.assert_called_once_with(args=[election_config.id], countdown=5)


@pytest.mark.django_db
@patch.object(tasks.import_election_eml_commits, "apply_async")
@patch.object(tasks, "GithubEmlFileHandler", autospec=True)
def test_import_task_queues_nothing_once_all_commits_are_imported(github_eml_file_handler, apply_async):
    election_config = ElectionConfigFactory()
    github_eml_file_handler.return_value.run.return_value = (1, False)

    import_election_eml_commits(election_config.id)

    apply_async.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "error",
    [
        RequestException("GitHub is unreachable"),
        RedisConnectionError("Redis is unreachable"),
    ],
)
@patch.object(tasks, "GithubEmlFileHandler", autospec=True)
def test_import_task_lets_file_handler_failures_escape_so_celery_can_retry(github_eml_file_handler, error):
    election_config = ElectionConfigFactory()
    github_eml_file_handler.return_value.run.side_effect = error

    # Swallowing this would leave the election silently stuck until the next beat tick
    with pytest.raises(type(error)):
        import_election_eml_commits(election_config.id)


@patch.object(build_polling_station_pv_zip, "delay")
@patch.object(tasks, "PDFFileHandler", autospec=True)
def test_import_pvs_runs_the_pdf_importer(pdf_file_handler, delay):
    handler = pdf_file_handler.return_value
    handler.run.return_value = 2
    handler.archive_gemeente_ids = set()

    assert import_pvs() == 2

    pdf_file_handler.assert_called_once_with(tasks.storages["pv_import"])
    handler.run.assert_called_once_with()
    delay.assert_not_called()


@patch.object(build_polling_station_pv_zip, "delay")
@patch.object(tasks, "PDFFileHandler", autospec=True)
def test_import_pvs_queues_one_zip_rebuild_per_gemeente_that_got_a_polling_station_form(pdf_file_handler, delay):
    handler = pdf_file_handler.return_value
    handler.run.return_value = 4
    handler.archive_gemeente_ids = {19, 17}

    assert import_pvs() == 4

    assert delay.call_args_list == [call(17), call(19)]


def test_setup_periodic_tasks_schedules_the_eml_and_pv_imports():
    sender = create_autospec(Celery, instance=True)

    setup_periodic_tasks(sender)

    # The name only shows up in beat's logs, so it is not worth pinning
    assert sender.add_periodic_task.call_args_list == [
        call(crontab(minute="*/10"), import_next_eml_commits.s(), name=ANY),
        call(crontab(minute="*/5"), import_pvs.s(), name=ANY),
    ]
