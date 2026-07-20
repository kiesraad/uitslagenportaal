from django.db import models


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


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
