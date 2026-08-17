from celery import Celery
from celery.schedules import crontab
from django.db import DatabaseError
from requests import RequestException

from election.models import ElectionConfig
from eml_import.utils.github_eml_importer import GithubEmlImporter
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
    autoretry_for=[DatabaseError, RequestException],
    retry_backoff=5,
    max_retries=2,
)
def import_next_eml_commits() -> None:
    election_configs = ElectionConfig.objects.all()
    for config in election_configs:
        GithubEmlImporter(config).run()
