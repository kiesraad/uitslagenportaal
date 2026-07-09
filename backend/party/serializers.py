from rest_framework import serializers

from mainsite.serializers import ElectionSummarySerializer
from party.models import Party


class PartyListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Party
        fields = (
            "id",
            "election_id",
            "registered_name",
        )


class PartyDetailSerializer(serializers.ModelSerializer):
    election = ElectionSummarySerializer(read_only=True)

    class Meta:
        model = Party
        fields = (
            "id",
            "registered_name",
            "election",
        )
