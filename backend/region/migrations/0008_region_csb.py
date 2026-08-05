import django.db.models.deletion
from django.db import migrations, models


def backfill_csb(apps, schema_editor):
    Region = apps.get_model("region", "Region")
    regions = list(Region.objects.all().only("id", "parent_id", "csb_id"))
    by_id = {region.id: region for region in regions}

    updates = []
    for region in regions:
        if not region.parent_id:
            continue
        ancestor = by_id[region.parent_id]
        while ancestor.parent_id:
            ancestor = by_id[ancestor.parent_id]
        if region.csb_id != ancestor.id:
            region.csb_id = ancestor.id
            updates.append(region)

    if updates:
        Region.objects.bulk_update(updates, ["csb_id"], batch_size=1000)


def clear_csb(apps, schema_editor):
    Region = apps.get_model("region", "Region")
    Region.objects.update(csb_id=None)


class Migration(migrations.Migration):
    dependencies = [
        ("region", "0007_merge_20260805_1133"),
    ]

    operations = [
        migrations.AddField(
            model_name="region",
            name="csb",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="csb_descendants",
                to="region.region",
            ),
        ),
        migrations.RunPython(backfill_csb, clear_csb),
    ]
