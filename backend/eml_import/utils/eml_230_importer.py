from pyeml_bindings import (
    Eml230,
)

from election.models import (
    Contest,
)
from eml_import.utils.eml_base_importer import EMLBaseImporter
from party.models import Candidate, Party


class EML230bImporter(EMLBaseImporter[Eml230]):
    """Kandidatenlijst"""

    def _get_election_identifier_data(self):
        return self.eml.candidate_list.election.election_identifier

    def _parse_data(self):
        assert len(self.eml.candidate_list.election.contest) == 1, "More than one contest, cannot parse"
        contest_data = self.eml.candidate_list.election.contest[0]
        contest, _ = Contest.objects.get_or_create(
            identifier=contest_data.contest_identifier.id,
            election=self.election,
        )
        candidates: list[Candidate] = []
        for affiliation in contest_data.affiliation:
            assert affiliation.affiliation_identifier.id, (
                f"AffiliationIdentifier/@Id missing for party "
                f"{affiliation.affiliation_identifier.registered_name or self.BLANCO_PARTY_REGISTERED_NAME}"
            )
            list_number = int(affiliation.affiliation_identifier.id)
            try:
                party = Party.objects.get(
                    election=self.election,
                    registered_name=affiliation.affiliation_identifier.registered_name,
                )
                party.list_number = list_number
                party.save(update_fields=["list_number", "updated_at"])
            except Party.DoesNotExist:
                # Some candidates are not affiliated to any party
                party, _ = Party.objects.get_or_create(
                    election=self.election,
                    registered_name=f"{self.BLANCO_PARTY_REGISTERED_NAME} {list_number}",
                    list_number=list_number,
                )

            for candidate in affiliation.candidate:
                first_name = None
                if candidate.candidate_full_name.person_name.first_name:
                    first_name = candidate.candidate_full_name.person_name.first_name.content[0]
                name_prefix = None
                if candidate.candidate_full_name.person_name.name_prefix:
                    name_prefix = candidate.candidate_full_name.person_name.name_prefix.content[0]
                candidates.append(
                    Candidate(
                        party=party,
                        contest=contest,
                        identifier=candidate.candidate_identifier.id,
                        position=candidate.candidate_identifier.id,
                        initials=candidate.candidate_full_name.person_name.name_line.content[0],
                        first_name=first_name,
                        name_prefix=name_prefix,
                        last_name=candidate.candidate_full_name.person_name.last_name.content[0],
                    )
                )

        if candidates:
            Candidate.objects.bulk_create(candidates, batch_size=self.BULK_BATCH_SIZE)
