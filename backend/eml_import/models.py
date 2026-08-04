from django.db import models

from mainsite.models import BaseModel


class ImportedCommit(BaseModel):
    commit_sha = models.CharField(max_length=40)
