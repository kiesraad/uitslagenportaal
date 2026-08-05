import factory
from factory.django import DjangoModelFactory

from eml_import.models import ImportedCommit


class ImportedCommitFactory(DjangoModelFactory):
    class Meta:
        model = ImportedCommit

    commit_sha = factory.Sequence(lambda n: f"{n:040x}")
