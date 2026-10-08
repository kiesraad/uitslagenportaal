import factory
from factory.django import DjangoModelFactory

from mainsite.models import RegionCategory
from pv_scraper.models import ScrapedFile, ScrapedPage, ScrapeSource


class ScrapeSourceFactory(DjangoModelFactory):
    class Meta:
        model = ScrapeSource

    code = factory.Sequence(lambda n: f"gm{n:04d}")
    kind = RegionCategory.GEMEENTE
    name = factory.Faker("city")
    website = factory.LazyAttribute(lambda o: f"https://www.{o.code}.nl/")


class ScrapedPageFactory(DjangoModelFactory):
    class Meta:
        model = ScrapedPage

    source = factory.SubFactory(ScrapeSourceFactory)
    url = factory.Sequence(lambda n: f"https://example.nl/page-{n}")
    root = factory.LazyAttribute(lambda o: o.url)
    depth = 0
    status = 200


class ScrapedFileFactory(DjangoModelFactory):
    class Meta:
        model = ScrapedFile

    source = factory.SubFactory(ScrapeSourceFactory)
    url = factory.Sequence(lambda n: f"https://example.nl/pv-{n}.pdf")
    sha256 = factory.Sequence(lambda n: f"{n:064x}")
    size = 1024
