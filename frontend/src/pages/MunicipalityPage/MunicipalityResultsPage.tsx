import {useParams} from 'react-router'
import RegionResultsContent from '../../components/ResultsPage/RegionResultsContent.tsx'
import {PageQueryBoundary} from '../../components/PageQueryBoundary.tsx'
import {useRegion} from '../../hooks/queries.ts'
import {useOutletContext} from "react-router";
import type {ElectionConfig} from "@/api/types.ts";
import HtmlHead from "@/components/HtmlHead.tsx";


export function MunicipalityResultsPage() {
  const {electionConfigSlug, regionSlug, csbSlug} = useParams<{
    electionConfigSlug: string;
    regionSlug: string;
    csbSlug?: string
  }>()
  const {electionConfig, municipalityTitle} = useOutletContext<{
    electionConfig: ElectionConfig,
    municipalityTitle: string
  }>();


  const {
    data: region,
    isLoading: isRegionLoading,
    isError: isRegionError,
    refetch: refetchRegion,
  } = useRegion(electionConfigSlug, regionSlug, csbSlug)

  const isLoading = isRegionLoading
  const isError = isRegionError || !electionConfig || !region

  if (isLoading || isError) {
    return (
      <PageQueryBoundary
        isLoading={isLoading}
        isError={isError}
        onRetry={() => {
          void refetchRegion()
        }}
        entityLabel="Gemeente"
      />
    )
  }

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
