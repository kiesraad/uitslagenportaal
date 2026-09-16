import factory
from factory.django import DjangoModelFactory

from election.tests.factories import ContestFactory, ElectionFactory
from party.models import Candidate, Party


class PartyFactory(DjangoModelFactory):
    class Meta:
        model = Party

    election = factory.SubFactory(ElectionFactory)
    registered_name = factory.Faker("company")


class CandidateFactory(DjangoModelFactory):
    class Meta:
        model = Candidate

    contest = factory.SubFactory(ContestFactory)
    party = factory.SubFactory(PartyFactory)
    identifier = factory.Sequence(lambda n: n)
    position = factory.Sequence(lambda n: n)
    last_name = factory.Faker("last_name")
