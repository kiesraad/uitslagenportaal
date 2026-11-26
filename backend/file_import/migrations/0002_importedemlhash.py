from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("eml_import", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ImportedEmlHash",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("sha256", models.CharField(max_length=64, unique=True)),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
