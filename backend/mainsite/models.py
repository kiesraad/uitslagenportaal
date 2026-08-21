from django.db import models


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CurrentQuerySet(models.QuerySet):
    def archive(self):
        return self.update(is_current=False)


class CurrentManager(models.Manager.from_queryset(CurrentQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(is_current=True)


class CurrentModel(BaseModel):
    """
    Soft-versioned domain row: corrections archive the old row and insert a new current one.

    ``objects`` is current-only. ``all_objects`` sees everything (FK base manager, importers).
    """

    is_current = models.BooleanField(default=True, db_index=True)

    objects = CurrentManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        base_manager_name = "all_objects"


class RegionCategory(models.TextChoices):
    STAAT = "STAAT", "Staat"
    WATERSCHAP = "WATERSCHAP", "Waterschap"
    KIESKRING = "KIESKRING", "Kieskring"
    GEMEENTE = "GEMEENTE", "Gemeente"
    PROVINCIE = "PROVINCIE", "Provincie"
    STEMBUREAU = "STEMBUREAU", "Stembureau"


class CountingMethod(models.TextChoices):
    # TODO: DSO: each SB has per-candidate votes, CSO: SB only has per-list totals
    CSO = "CSO", "Centrale Stemopname"
    DSO = "DSO", "Decentrale Stemopname"
