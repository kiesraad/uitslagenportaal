from django.db import migrations


class Migration(migrations.Migration):
    """
    Remove TimelineEntry, now copied to TimelineDate, and the table django.contrib.admin left behind.

    django_admin_log's foreign key to auth_user makes `flush` fail, as flush only truncates tables of installed apps.
    """

    dependencies = [
        ("election", "0041_timelineentry_to_timelinedate"),
    ]

    operations = [
        migrations.DeleteModel(
            name="TimelineEntry",
        ),
        migrations.RunSQL("DROP TABLE IF EXISTS django_admin_log", reverse_sql=migrations.RunSQL.noop),
    ]
