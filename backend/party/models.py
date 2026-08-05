from django.db import models

from mainsite.models import BaseModel
from mainsite.utils.utils import name_to_slug


class Party(BaseModel):
    election = models.ForeignKey(
        "election.Election",
        on_delete=models.CASCADE,
        related_name="parties",
    )
    registered_name = models.CharField(max_length=255)
    list_number = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["election", "registered_name"],
                name="unique_registered_name_per_election",
            )
        ]

    # This slug is not unique, as it is used in combination with election
    # and the region type to retrieve it as opposed to only using the slug
    slug = models.SlugField(unique=False, db_index=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = f"{name_to_slug(self.registered_name)}"[:49]
        super().save(*args, **kwargs)


class Candidate(BaseModel):
    contest = models.ForeignKey(
        "election.Contest",
        on_delete=models.CASCADE,
        related_name="candidates",
    )
    party = models.ForeignKey(
        "party.Party",
        on_delete=models.CASCADE,
        related_name="candidates",
    )
    identifier = models.PositiveIntegerField()
    position = models.PositiveIntegerField()
    initials = models.CharField(max_length=64, blank=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    name_prefix = models.CharField(max_length=128, null=True, blank=True)
    last_name = models.CharField(max_length=255)
