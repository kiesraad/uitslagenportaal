import django.db.models.manager
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("election", "0027_current_model_is_current"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="electiondocument",
            options={"base_manager_name": "all_objects"},
        ),
        migrations.AlterModelManagers(
            name="electiondocument",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("all_objects", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AddField(
            model_name="electiondocument",
            name="is_current",
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AddConstraint(
            model_name="electiondocument",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_current", True)),
                fields=("region", "file_type"),
                name="unique_current_document_per_region_and_file_type",
            ),
        ),
    ]
