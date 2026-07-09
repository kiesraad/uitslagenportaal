from django.db import models


class Election(models.Model):
    election_id = models.CharField(max_length=32, unique=True)
    election_name = models.CharField(max_length=255)
    election_category = models.CharField(max_length=2)
    election_subcategory = models.CharField(max_length=8, blank=True, default="")
    election_date = models.DateField(null=True, blank=True)
    nomination_date = models.DateField(null=True, blank=True)
    number_of_seats = models.PositiveIntegerField(null=True, blank=True)
    preference_threshold = models.PositiveIntegerField(null=True, blank=True)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    deleted_on = models.DateTimeField(null=True, default=None)

    def __str__(self):
        return self.election_name


class Region(models.Model):
    election = models.ForeignKey(
        Election, on_delete=models.CASCADE, related_name="regions"
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, related_name="children", null=True, blank=True
    )
    region_category = models.CharField(max_length=16)
    region_number = models.CharField(max_length=16)
    region_name = models.CharField(max_length=255)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    deleted_on = models.DateTimeField(null=True, default=None)

    class Meta:
        indexes = [
            models.Index(fields=["election", "region_category", "region_number"]),
            models.Index(fields=["election", "parent"]),
        ]

    def __str__(self):
        return self.region_name


class PollingStation(models.Model):
    municipality = models.ForeignKey(
        Region, on_delete=models.CASCADE, related_name="polling_stations"
    )
    pollingstation_code = models.CharField(max_length=16)
    pollingstation_name = models.CharField(max_length=255)
    pollingstation_zipcode = models.CharField(max_length=16, blank=True)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    deleted_on = models.DateTimeField(null=True, default=None)

    class Meta:
        indexes = [models.Index(fields=["pollingstation_code"])]

    def __str__(self):
        return self.pollingstation_name


class Contest(models.Model):
    election = models.ForeignKey(
        Election, on_delete=models.CASCADE, related_name="contests"
    )
    kieskring = models.ForeignKey(
        Region,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="contests",
    )
    contest_id = models.CharField(max_length=32)
    contest_name = models.CharField(max_length=128, blank=True)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    deleted_on = models.DateTimeField(null=True, default=None)

    def __str__(self):
        return self.contest_name


class Affiliation(models.Model):
    contest = models.ForeignKey(
        Contest, on_delete=models.CASCADE, related_name="affiliations"
    )
    affiliation_id = models.IntegerField()
    affiliation_name = models.CharField(max_length=255)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    deleted_on = models.DateTimeField(null=True, default=None)

    def __str__(self):
        return self.affiliation_name


class Candidate(models.Model):
    affiliation = models.ForeignKey(
        Affiliation, on_delete=models.CASCADE, related_name="candidates"
    )
    cand_id = models.IntegerField()
    initials = models.CharField(max_length=32, blank=True)
    first_name = models.CharField(max_length=128, blank=True)
    prefix = models.CharField(max_length=64, blank=True)
    last_name = models.CharField(max_length=128, blank=True)
    gender = models.CharField(max_length=16, blank=True)
    locality = models.CharField(max_length=128, blank=True)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    deleted_on = models.DateTimeField(null=True, default=None)

    def __str__(self):
        return self.last_name


class Telling(models.Model):
    election = models.ForeignKey(
        Election, on_delete=models.CASCADE, related_name="tellingen"
    )
    contest = models.ForeignKey(
        Contest, on_delete=models.CASCADE, related_name="tellingen"
    )
    region = models.ForeignKey(
        Region, on_delete=models.CASCADE, related_name="tellingen"
    )
    telling_kind = models.CharField(max_length=16)  # TELLING, TOTAALTELLING
    telling_level = models.CharField(
        max_length=16
    )  # GEMEENTE, KIESKRING, PROVINCIE, STAAT
    authority_id = models.CharField(max_length=64, blank=True, default="")
    authority_name = models.CharField(max_length=255, blank=True, default="")
    uploaded_at = models.DateTimeField()
    # TODO: Can otherwise implement this as is_corrigenda since CRUD takes care of currentness
    is_current_version = models.BooleanField(default=True)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    deleted_on = models.DateTimeField(null=True, default=None)

    def __str__(self):
        return self.authority_name


class ResultUnit(models.Model):
    TOTAL, POLLING_STATION, SUBREGION = "TOTAL", "POLLING_STATION", "SUBREGION"

    submission = models.ForeignKey(
        Telling, on_delete=models.CASCADE, related_name="result_units"
    )
    polling_station = models.ForeignKey(
        PollingStation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="result_units",
    )
    subregion = models.ForeignKey(
        Region,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="result_units",
    )
    unit_type = models.CharField(max_length=16)  # TOTAL, POLLING_STATION, SUBREGION
    unit_id = models.CharField(max_length=64, blank=True)  # 0744::SB2 or 0106
    unit_label = models.CharField(max_length=255, blank=True)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    deleted_on = models.DateTimeField(null=True, default=None)

    def __str__(self):
        return self.unit_id


class AffiliationVote(models.Model):
    telling = models.ForeignKey(
        ResultUnit, on_delete=models.CASCADE, related_name="affiliation_results"
    )
    affiliation = models.ForeignKey(
        Affiliation, on_delete=models.CASCADE, related_name="affiliation_results"
    )
    affiliation_valid_votes = models.PositiveIntegerField(default=0)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    deleted_on = models.DateTimeField(null=True, default=None)

    def __str__(self):
        return self.affiliation.affiliation_name


class CandidateVote(models.Model):
    telling = models.ForeignKey(
        ResultUnit, on_delete=models.CASCADE, related_name="candidate_results"
    )
    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name="candidate_results"
    )
    candidate_valid_votes = models.PositiveIntegerField(default=0)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    deleted_on = models.DateTimeField(null=True, default=None)

    def __str__(self):
        return self.candidate.last_name


class UnitSummary(models.Model):
    unit = models.OneToOneField(
        ResultUnit, on_delete=models.CASCADE, related_name="unit_summary"
    )
    cast = models.IntegerField(null=True)
    total_counted = models.IntegerField(null=True)
    rejected_invalid = models.IntegerField(default=0)
    rejected_blank = models.IntegerField(default=0)
    geldige_stempassen = models.IntegerField(null=True)
    geldige_volmachtbewijzen = models.IntegerField(null=True)
    geldige_kiezerspassen = models.IntegerField(null=True)
    toegelaten_kiezers = models.IntegerField(null=True)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    deleted_on = models.DateTimeField(null=True, default=None)

    # TODO: Implement later, misschien handig?
    # meer_getelde_stembiljetten = models.IntegerField(null=True)
    # minder_getelde_stembiljetten = models.IntegerField(null=True)
    # meegenomen_stembiljetten = models.IntegerField(null=True)
    # te_veel_uitgereikte_stembiljetten = models.IntegerField(null=True)
    # te_weinig_uitgereikte_stembiljetten = models.IntegerField(null=True)
    # geen_verklaring = models.IntegerField(null=True)
    # andere_verklaring = models.IntegerField(null=True)
    # geen_briefstembiljetten = models.IntegerField(null=True)
    # kwijtgeraakte_stembiljetten = models.IntegerField(null=True)
    # te_veel_briefstembiljetten = models.IntegerField(null=True)
