from rest_framework import serializers

from election.models import Election, VoteCount, VoterTurnoutCount
from party.models import Candidate, Party
from region.models import Region


class ElectionSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Election
        fields = (
            "id",
            "name",
            "subcategory",
            "date",
        )


class RegionSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = (
            "id",
            "election_id",
            "parent_id",
            "region_number",
            "region_category",
            "region_name",
            "slug",
        )


class CandidateSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = (
            "position",
            "initials",
            "first_name",
            "name_prefix",
            "last_name",
        )


class PartySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Party
        fields = ("registered_name", "slug")


class VoteCountSummarySerializer(serializers.ModelSerializer):
    candidate = CandidateSummarySerializer(many=False)
    party = PartySummarySerializer(many=False)

    class Meta:
        model = VoteCount
        fields = ("id", "valid_votes", "candidate", "party", "result_level", "eml_type")


class VoterTurnoutCountSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = VoterTurnoutCount
        fields = ("category", "reason_code", "votes")
