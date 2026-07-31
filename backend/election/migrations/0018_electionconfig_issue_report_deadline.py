import datetime
from zoneinfo import ZoneInfo

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("election", "0017_election_slug"),
    ]

    operations = [
        migrations.AddField(
            model_name="electionconfig",
            name="issue_report_deadline",
            field=models.DateTimeField(
                default=datetime.datetime(2026, 12, 14, 10, 0, tzinfo=ZoneInfo("Europe/Amsterdam")),
            ),
        ),
    ]
