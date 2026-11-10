import django.db.models.deletion
from django.db import migrations, models


def delete_unlinked_hashes(apps, schema_editor):
    # Existing hashes cannot be traced to an election, so a wipe would never remove them
    ImportedEmlHash = apps.get_model("eml_import", "ImportedEmlHash")
    ImportedEmlHash.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("election", "0035_merge_20260917_1317"),
        ("eml_import", "0002_importedemlhash"),
    ]

    operations = [
        migrations.RunPython(delete_unlinked_hashes, migrations.RunPython.noop),
        migrations.AddField(
            model_name="importedemlhash",
            name="election",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="election.election",
            ),
        ),
    ]
