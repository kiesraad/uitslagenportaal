from django.db import migrations, models

from mainsite.utils.utils import name_to_slug


def populate_election_slugs(apps, schema_editor):
    Election = apps.get_model("election", "Election")
    ElectionConfig = apps.get_model("election", "ElectionConfig")
    config_identifiers = {
        config.id: config.identifier for config in ElectionConfig.objects.all()
    }
    used_slugs = set()

    for election in Election.objects.order_by("id"):
        base_slug = name_to_slug(election.name)[:49]
        slug = base_slug
        suffix = 2
        while slug in used_slugs:
            slug = f"{base_slug[:45]}-{suffix}"
            suffix += 1
        used_slugs.add(slug)
        election.slug = slug
        election.save(update_fields=["slug"])


class Migration(migrations.Migration):
    dependencies = [
        ("election", "0016_remove_electionconfig_csb_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="election",
            name="slug",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.RunPython(populate_election_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="election",
            name="slug",
            field=models.CharField(db_index=True, max_length=64, unique=True),
        ),
    ]
