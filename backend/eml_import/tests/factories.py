import factory
from factory.django import DjangoModelFactory

from election.tests.factories import ElectionConfigFactory
from eml_import.models import BranchType, ImportedCommit


class ImportedCommitFactory(DjangoModelFactory):
    class Meta:
        model = ImportedCommit

    election_config = factory.SubFactory(ElectionConfigFactory)
    branch_type = BranchType.EXCHANGE
    commit_sha = factory.Sequence(lambda n: f"{n:040x}")
