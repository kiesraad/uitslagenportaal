import logging

from botocore.exceptions import ConnectionError as S3ConnectionError
from celery import Celery
from celery.exceptions import BackendError
from celery.schedules import crontab
from django.db import DatabaseError
from redis.exceptions import ConnectionError as RedisConnectionError
from requests import RequestException

from election.models import ElectionConfig
from eml_import.utils.github_eml_file_handler import GithubEmlFileHandler
from mainsite.celery import app

logger = logging.getLogger(__name__)


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
    autoretry_for=[DatabaseError, RequestException, RedisConnectionError, S3ConnectionError],
    retry_backoff=5,
    max_retries=2,
)
def import_election_eml_commits(election_config_id: int) -> tuple[int, bool]:
    """
    Import the next EML commit from GitHub for the given election config.
    By running a task for each election config, we can retry on error for each election instead of all at once.
    A new task will be scheduled if commits remain to be processed. Every 10 min. the chain is restarted
    by import_next_eml_commits() in case it was broken.
    :param election_config_id:
    """
    election_config = ElectionConfig.objects.get(pk=election_config_id)
    files_processed, commits_remaining = GithubEmlFileHandler(election_config).run()

    # Schedule the next task in a few seconds if there are unprocessed commits
    if commits_remaining:
        logger.info("Scheduling next task for election config id=%d...", election_config_id)
        import_election_eml_commits.apply_async(args=[election_config_id], countdown=2)

    return files_processed, commits_remaining
