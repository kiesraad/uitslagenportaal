from rest_framework import serializers

from election.models import Election, VoteCount, VoterTurnoutCount
from region.models import Region
from party.models import Candidate, Party


class ElectionSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Election
        fields = (
            "id",
            "identifier",
            "name",
            "category",
            "date",
            "nomination_date",
            "number_of_seats",
            "preference_threshold",
        )


class RegionSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = (
            "id",
            "election_id",
            "parent_id",
            "number",
            "category",
            "name",
            "level",
            "display_order",
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
        fields = ("id", "valid_votes", "candidate", "party", "result_level")


class VoterTurnoutCountSummarySerializer(serializers.ModelSerializer):

    class Meta:
        model = VoterTurnoutCount
        fields = ("category", "reason_code", "votes")
