from django.db import migrations

# Entries were free text; their titles are the step names the frontend now hardcodes.
TITLE_EVENTS = {
    "telling in de stembureaus": "sb_vote_count",
    "optelling per gemeente": "municipality_vote_count",
    "optelling per kieskring": "electoral_district_vote_count",
    "centraal stembureau controleert": "csb_check",
    "de kiesraad publiceert de uitslag": "csb_result_publish",
}


def copy_entries_to_dates(apps, schema_editor):
    """Give each config one date per known step, preferring the DEFAULT variant; unknown titles are dropped."""
    TimelineEntry = apps.get_model("election", "TimelineEntry")
    TimelineDate = apps.get_model("election", "TimelineDate")

    seen = set()
    dates = []
    entries = TimelineEntry.objects.order_by("election_config_id", "date")
    # Stable sort: DEFAULT entries first per config, each group still by date.
    for entry in sorted(entries, key=lambda e: (e.election_config_id, e.variant != "DEFAULT")):
        event = TITLE_EVENTS.get(entry.title_nl.strip().lower())
        if event is None or (entry.election_config_id, event) in seen:
            continue
        seen.add((entry.election_config_id, event))
        dates.append(TimelineDate(election_config_id=entry.election_config_id, event=event, date=entry.date))
    TimelineDate.objects.bulk_create(dates)


class Migration(migrations.Migration):
    dependencies = [
        ("election", "0040_timelinedate"),
    ]

    operations = [
        migrations.RunPython(copy_entries_to_dates, reverse_code=migrations.RunPython.noop),
    ]
