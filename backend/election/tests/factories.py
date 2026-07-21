import datetime

import factory
from factory.django import DjangoModelFactory

from election.models import (
    Contest,
    Election,
    ElectionConfig,
    ElectionDocument,
    TimelineEntry,
    TimelineEntryStatus,
    TimelineVariant,
)

CATEGORIES = ["GR", "TK", "AB", "PS", "EP"]


class ElectionConfigFactory(DjangoModelFactory):
    class Meta:
        model = ElectionConfig

    identifier = factory.Sequence(lambda n: f"{CATEGORIES[n % len(CATEGORIES)]}202{n}")
    category = factory.Faker("random_element", elements=CATEGORIES)
    date = factory.Faker("date_time_this_decade", tzinfo=datetime.timezone.utc)


class ElectionFactory(DjangoModelFactory):
    class Meta:
        model = Election

    election_config = factory.SubFactory(ElectionConfigFactory)
    name = factory.Faker("city")
    subcategory = factory.Faker("random_element", elements=CATEGORIES)
    date = factory.Faker("date_this_decade")


class TimelineEntryFactory(DjangoModelFactory):
    class Meta:
        model = TimelineEntry

    election_config = factory.SubFactory(ElectionConfigFactory)
    variant = TimelineVariant.DEFAULT
    status = TimelineEntryStatus.PENDING
    title = factory.Faker("sentence", nb_words=4)
    date = factory.Faker("date_time_this_decade", tzinfo=datetime.timezone.utc)
    body = factory.Faker("paragraph")


class ContestFactory(DjangoModelFactory):
    class Meta:
        model = Contest

    identifier = factory.Sequence(lambda n: f"contest-{n}")
    election = factory.SubFactory(ElectionFactory)


class ElectionDocumentFactory(DjangoModelFactory):
    class Meta:
        model = ElectionDocument

    storage_key = factory.Sequence(lambda n: f"document-{n}.xml")
    content_type = "application/xml"
    size = factory.Faker("random_int", min=1, max=10_000)
