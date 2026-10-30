from django.db import models
from django.db.models import Q

from mainsite.models import BaseModel, CountingMethod, RegionCategory
from mainsite.utils.utils import name_to_slug


def build_region_slug(region_number, region_name: str) -> str:
    """
    Derive a Region slug from its number and name.

    Kept separate from Region.save() so bulk_create() callers can precompute the
    exact same slug instead of duplicating the logic. A region without a number
    (e.g. the CSB of a national election) gets a slug of just its name.
    """
    if not region_number:
        return name_to_slug(region_name)[:49]
    number_slug = str(region_number)
    if "::" in number_slug:
        # region_number can contain "::" (e.g. stembureau ids); keep URL-safe
        number_slug = number_slug.split("::")[1]
    return f"{number_slug}-{name_to_slug(region_name)}"[:49]


def parse_station_number(region_number: str | None) -> int | None:
    """Polling-station number from a stembureau region_number (`0203::SB1` → 1)."""
    if not region_number:
        return None
    station = str(region_number).split("::")[-1].removeprefix("SB")
    return int(station) if station.isdigit() else None


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
    csb = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="csb_descendants",
    )

    region_number = models.CharField(max_length=32, null=True)
    region_category = models.CharField(
        max_length=32,
        choices=RegionCategory.choices,
    )
    region_name = models.CharField(max_length=255, db_index=True)
    # Stembureaus only; together with region_name it identifies the voting location.
    postal_code = models.CharField(max_length=16, null=True, blank=True)

    counting_method = models.CharField(
        max_length=3,
        choices=CountingMethod.choices,
        null=True,
        blank=True,
    )
    results_available_at = models.DateTimeField(null=True)

    # This slug is not unique, as it is used in combination with election
    # and the region type to retrieve it as opposed to only using the slug
    slug = models.SlugField(unique=False, db_index=True)

    @property
    def station_number(self) -> int | None:
        """Polling-station number from region_number (`0203::SB1` → 1); otherwise None."""
        if self.region_category != RegionCategory.STEMBUREAU:
            return None
        return parse_station_number(self.region_number)

    @property
    def is_csb(self) -> bool:
        return self.region_category == self.election.election_config.csb_type

    @property
    def hsb(self) -> Region | None:
        if self.region_category not in [RegionCategory.STEMBUREAU, RegionCategory.GEMEENTE]:
            return None
        return Region.objects.filter(
            Q(region_category=RegionCategory.KIESKRING) & (Q(children=self) | Q(children__children=self))
        ).first()

    @property
    def has_hsb(self) -> bool:
        """
        A single HSB for a region means it's skipped in the counting process,
        only return true if the HSB takes part in the vote counting hierarchy.
        """
        return self.csb is not None and self.csb.children.filter(region_category=RegionCategory.KIESKRING).count() > 1

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = build_region_slug(self.region_number, self.region_name)
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

    def __str__(self) -> str:
        return f"<Region {self.region_category.lower()} {self.region_name} ({self.pk})>"


def hsb_kieskringen(regions: models.QuerySet[Region]) -> models.QuerySet[Region]:
    """The kieskringen among regions that have their own HSB (EML_510c).

    Only a kieskring that shares its CSB with other kieskringen does; a CSB with a single kieskring (a WS, or a PS
    province such as Drenthe) counts that kieskring itself.
    """
    kieskringen = regions.filter(region_category=RegionCategory.KIESKRING)
    shared_csbs = kieskringen.values("parent").annotate(count=models.Count("id")).filter(count__gt=1)
    return kieskringen.filter(parent__in=shared_csbs.values("parent"))
