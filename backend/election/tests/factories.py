import datetime

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from election.models import (
    Contest,
    Election,
    ElectionCategory,
    ElectionConfig,
    ElectionDocument,
    TimelineDate,
    TimelineEvent,
)

CATEGORIES = ElectionCategory.values


class ElectionConfigFactory(DjangoModelFactory):
    class Meta:
        model = ElectionConfig

    identifier = factory.Sequence(lambda n: f"{CATEGORIES[n % len(CATEGORIES)]}202{n}")
    category = factory.Faker("random_element", elements=CATEGORIES)
    date = factory.LazyFunction(lambda: timezone.now() - datetime.timedelta(days=1))


class ElectionFactory(DjangoModelFactory):
    class Meta:
        model = Election

    election_config = factory.SubFactory(ElectionConfigFactory)
    name = factory.Faker("city")
    subcategory = factory.Faker("random_element", elements=CATEGORIES)
    date = factory.Faker("date_this_decade")


class TimelineDateFactory(DjangoModelFactory):
    class Meta:
        model = TimelineDate

    election_config = factory.SubFactory(ElectionConfigFactory)
    event = TimelineEvent.SB_VOTE_COUNT
    date = factory.Faker("date_time_this_decade", tzinfo=datetime.timezone.utc)


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


class CertifiedElectionDocumentFactory(ElectionDocumentFactory):
    storage_key = factory.Sequence(lambda n: f"TK2025/document-{n}.pdf")
    content_type = "application/pdf"
    file_type = ElectionDocument.FileType.PDF_NA31_2
