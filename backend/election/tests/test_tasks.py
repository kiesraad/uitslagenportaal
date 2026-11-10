from unittest.mock import ANY, create_autospec, patch

import pytest
from botocore.exceptions import ConnectionError as S3ConnectionError
from celery import Celery
from celery.schedules import crontab

from election import tasks
from election.tasks import import_election_configs, setup_periodic_tasks


@patch.object(tasks, "import_new_election_configs")
def test_import_election_configs_returns_the_number_imported(import_new_election_configs):
    import_new_election_configs.return_value = 2

    assert import_election_configs() == 2


@patch.object(tasks, "import_new_election_configs")
def test_import_election_configs_lets_storage_failures_escape_so_celery_can_retry(import_new_election_configs):
    import_new_election_configs.side_effect = S3ConnectionError(error="unreachable")

    # Swallowing this would leave new election configs silently unimported until the next beat tick
    with pytest.raises(S3ConnectionError):
        import_election_configs()


def test_setup_periodic_tasks_schedules_the_import_every_five_minutes():
    sender = create_autospec(Celery, instance=True)

    setup_periodic_tasks(sender)

    sender.add_periodic_task.assert_called_once_with(crontab(minute="*/5"), import_election_configs.s(), name=ANY)
