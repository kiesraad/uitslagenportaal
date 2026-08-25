from celery import Celery
from celery.exceptions import BackendError
from celery.schedules import crontab
from django.db import DatabaseError
from requests import RequestException

from election.models import ElectionConfig
from eml_import.utils.github_eml_importer import GithubEmlFileHandler
from mainsite.celery import app


@app.on_after_finalize.connect
def setup_periodic_tasks(sender: Celery, **_) -> None:
    # Run the `import_next_eml_commits` task every 10 min
    sender.add_periodic_task(
        crontab(minute="*/10"),
        import_next_eml_commits.s(),
        name="Import next EML commits from Github",
    )


@app.task(
    ignore_result=True,
    autoretry_for=[DatabaseError, BackendError],
    retry_backoff=5,
    max_retries=2,
)
def import_next_eml_commits() -> None:
    """
    Start a new task for each election config.
    """
    election_configs = ElectionConfig.objects.all()
    for config in election_configs:
        import_election_eml_commits.delay(config.id)


@app.task(
    ignore_result=True,
    autoretry_for=[DatabaseError, RequestException],
    retry_backoff=5,
    max_retries=2,
)
def import_election_eml_commits(election_config_id: int) -> None:
    """
    Import the next EML commits from GitHub for the given election config.
    By running a task for each election config, we can retry on error for each election instead of all at once.
    :param election_config_id:
    """
    election_config = ElectionConfig.objects.get(pk=election_config_id)
    GithubEmlFileHandler(election_config).run()
