import logging

from botocore.exceptions import ConnectionError as S3ConnectionError
from celery import Celery
from celery.schedules import crontab
from django.db import DatabaseError

from election.election_config_storage import import_new_election_configs
from mainsite.celery import app

logger = logging.getLogger(__name__)


@app.on_after_finalize.connect
def setup_periodic_tasks(sender: Celery, **_) -> None:
    sender.add_periodic_task(
        crontab(minute="*/5"),
        import_election_configs.s(),
        name="Import new election configs from object storage",
    )


@app.task(
    ignore_result=True,
    autoretry_for=[DatabaseError, S3ConnectionError],
    retry_backoff=5,
    max_retries=2,
)
def import_election_configs() -> int:
    """
    Import any new or changed election_config JSON files from object storage.
    """
    imported = import_new_election_configs()
    if imported:
        logger.info("Imported %d election config(s) from object storage.", imported)
    return imported
