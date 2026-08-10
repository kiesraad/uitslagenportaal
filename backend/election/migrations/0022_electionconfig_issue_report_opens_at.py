import datetime
from zoneinfo import ZoneInfo

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("election", "0021_merge_20260810_1229"),
    ]

    operations = [
        migrations.AddField(
            model_name="electionconfig",
            name="issue_report_opens_at",
            field=models.DateTimeField(
                default=datetime.datetime(2026, 12, 8, 9, 0, tzinfo=ZoneInfo("Europe/Amsterdam")),
            ),
        ),
    ]
