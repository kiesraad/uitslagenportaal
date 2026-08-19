import RegionResultsContent from '../../components/ResultsPage/RegionResultsContent.tsx'
import {useOutletContext, useParams} from "react-router";
import type {ElectionConfig, Region} from "@/api/types.ts";
import HtmlHead from "@/components/HtmlHead.tsx";


export function MunicipalityResultsPage() {
  const {electionConfig, region, municipalityTitle} = useOutletContext<{
    electionConfig: ElectionConfig,
    region: Region,
    municipalityTitle: string
  }>();

  return (
    <>
      <HtmlHead title={`Resultaten ${municipalityTitle}`}/>
      <div className="page-main page-main-two-columns">
        <div className="page-space-3">
          <RegionResultsContent
            intro={
              <>
                Het gemeentelijk stembureau heeft de telresultaten van alle stembureaus in {region.region_name} gecontroleerd,
                overgenomen en bij elkaar opgeteld. Hieronder ziet u de telresultaten zoals ze zijn
                opgenomen in het proces-verbaal van de gemeente.
              </>
            }
            voteCounts={region.vote_counts}
            turnoutVotes={region.voter_turnout_counts}
            reports={{
              description: "Onderstaande documenten bevatten de laatste telresultaten van de gemeente, zoals ze worden meegeteld in de uitslag. De getallen in het overzicht hierboven komen uit het EML_NL tellingbestand.",
              documents: region.documents,
            }}
            timelineVariant={region.timeline_variant}
            timelineEntries={electionConfig.timeline_entries ?? []}
            issueReportDeadline={electionConfig.issue_report_deadline}
            notPublishedRegionLabel={region.region_name}
          />
        </div>
      </div>
    </>
  )
}
