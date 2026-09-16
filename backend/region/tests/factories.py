import factory
from factory.django import DjangoModelFactory

from election.tests.factories import ElectionFactory
from mainsite.models import RegionCategory
from region.models import Region


class RegionFactory(DjangoModelFactory):
    class Meta:
        model = Region

    election = factory.SubFactory(ElectionFactory)
    region_number = factory.Sequence(lambda n: str(n))
    region_category = RegionCategory.GEMEENTE
    region_name = factory.Faker("city")
