from django.db import models

from mainsite.models import BaseModel, CountingMethod, RegionCategory
from mainsite.utils.utils import name_to_slug


class Region(BaseModel):
    election = models.ForeignKey(
        "election.Election",
        on_delete=models.CASCADE,
        related_name="regions",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )

    region_number = models.CharField(max_length=32)
    region_category = models.CharField(
        max_length=32,
        choices=RegionCategory.choices,
    )
    region_name = models.CharField(max_length=255, db_index=True)

    counting_method = models.CharField(
        max_length=3,
        choices=CountingMethod.choices,
        default=CountingMethod.CSO,
        null=True,
        blank=True,
    )
    results_available_at = models.DateTimeField(null=True)

    # This slug is not unique, as it is used in combination with election
    # and the region type to retrieve it as opposed to only using the slug
    slug = models.SlugField(unique=False, db_index=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            number_slug = str(self.region_number)
            if "::" in number_slug:
                # region_number can contain "::" (e.g. stembureau ids); keep URL-safe
                number_slug = number_slug.split("::")[1]
            self.slug = f"{number_slug}-{name_to_slug(self.region_name)}"[:49]
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["election", "slug", "region_category", "parent"],
                name="unique_region_identifier_per_election",
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.parent_id and self.parent.election_id != self.election_id:
            raise ValidationError({"parent": "Parent region must belong to the same election."})
