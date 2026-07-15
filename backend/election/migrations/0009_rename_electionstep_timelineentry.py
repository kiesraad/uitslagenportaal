import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('election', '0008_alter_electionstep_options'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ElectionStep',
            new_name='TimelineEntry',
        ),
        migrations.RenameField(
            model_name='timelineentry',
            old_name='state',
            new_name='status',
        ),
        migrations.AlterField(
            model_name='timelineentry',
            name='election_config',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='timeline_entries',
                to='election.electionconfig',
            ),
        ),
    ]
