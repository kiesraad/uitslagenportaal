from rest_framework import serializers
from .models import (
    Election,
    Region,
    PollingStation,
    Affiliation,
    Candidate,
    ResultUnit,
    AffiliationVote,
    CandidateVote,
    UnitSummary,
)


class ElectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Election
        fields = [
            "election_id",
            "name",
            "category",
            "subcategory",
            "election_date",
            "number_of_seats",
        ]


class RegionSerializer(serializers.ModelSerializer):
    parent_region_number = serializers.CharField(
        source="parent.region_number", read_only=True, default=None
    )

    class Meta:
        model = Region
        fields = ["region_number", "category", "name", "parent_region_number"]


class PollingStationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollingStation
        fields = ["sb_code", "name", "zipcode"]


class PartyVoteSerializer(serializers.ModelSerializer):
    affiliation_id = serializers.IntegerField(source="affiliation.affiliation_id")
    name = serializers.CharField(source="affiliation.name")

    class Meta:
        model = AffiliationVote
        fields = ["affiliation_id", "name", "valid_votes"]


# TODO: Check with Chris
class SummarySerializer(serializers.ModelSerializer):
    stempassen = serializers.IntegerField(source="geldige_stempassen")
    volmachtbewijzen = serializers.IntegerField(source="geldige_volmachtbewijzen")
    kiezerspassen = serializers.IntegerField(source="geldige_kiezerspassen")
    toegelaten_kiezers = serializers.IntegerField()
    stemmen_op_kandidaten = serializers.IntegerField(source="total_counted")
    blanco = serializers.IntegerField(source="rejected_blank")
    ongeldig = serializers.IntegerField(source="rejected_invalid")
    totaal_uitgebracht = serializers.IntegerField(source="cast")

    class Meta:
        model = UnitSummary
        fields = [
            "stempassen",
            "volmachtbewijzen",
            "kiezerspassen",
            "toegelaten_kiezers",
            "stemmen_op_kandidaten",
            "blanco",
            "ongeldig",
            "totaal_uitgebracht",
        ]


class UnitResultSerializer(serializers.Serializer):
    label = serializers.CharField()
    summary = SummarySerializer()
    partijen = PartyVoteSerializer(many=True)

    @classmethod
    def from_unit(cls, unit):
        summary = getattr(unit, "summary", None)
        return cls(
            {
                "label": unit.label or unit.raw_unit_id,
                "summary": summary,
                "partijen": unit.affiliation_results.all(),
            }
        )


class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = [
            "candidate_id",
            "initials",
            "first_name",
            "prefix",
            "last_name",
            "gender",
            "locality",
        ]


class CandidateVoteSerializer(serializers.ModelSerializer):
    candidate = CandidateSerializer()

    class Meta:
        model = CandidateVote
        fields = ["candidate", "valid_votes"]
