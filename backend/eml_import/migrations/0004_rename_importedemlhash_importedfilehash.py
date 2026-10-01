from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("eml_import", "0003_importedemlhash_election"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="ImportedEmlHash",
            new_name="ImportedFileHash",
        ),
    ]
