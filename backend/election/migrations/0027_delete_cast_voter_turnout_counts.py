from django.db import migrations


def delete_cast_turnout_counts(apps, schema_editor):
    VoterTurnoutCount = apps.get_model("election", "VoterTurnoutCount")
    VoterTurnoutCount.objects.filter(category="TOTALS", reason_code="cast").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("election", "0026_contest_name_alter_electionconfig_category"),
    ]

    operations = [
        migrations.RunPython(delete_cast_turnout_counts, migrations.RunPython.noop),
    ]
