from django.db import migrations


class Migration(migrations.Migration):
    """
    Drop the table django.contrib.admin left behind when it was uninstalled.

    Its foreign key to auth_user makes `flush` fail, as flush only truncates tables of installed apps.
    """

    dependencies = [
        ("election", "0040_timelinedate_delete_timelineentry"),
    ]

    operations = [
        migrations.RunSQL("DROP TABLE IF EXISTS django_admin_log", reverse_sql=migrations.RunSQL.noop),
    ]
