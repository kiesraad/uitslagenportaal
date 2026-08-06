import {useMemo} from 'react'
import {useParams} from 'react-router-dom'
import VotesResume from '../../components/ResultsPage/VotesResume.tsx'
import VotesList from '../../components/ResultsPage/VotesList.tsx'
import ReportsWithResults from '../../components/ResultsPage/ReportsWithResults.tsx'
import ResultsNotPublished from '../../components/ResultsPage/ResultsNotPublished.tsx'
import ResultsTimeline from '../../components/ResultsPage/ResultsTimeline'
import {PageQueryBoundary} from '../../components/PageQueryBoundary.tsx'
import {useRegion} from '../../hooks/queries.ts'
import PageIndex from '../../components/PageIndex'
import IssueNotice from '../../components/ResultsPage/IssueNotice.tsx'
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

  const hasResults = Array.isArray(region?.vote_counts) && region.vote_counts.length > 0

  const partyLevelVoteCounts = useMemo(
    () => region?.vote_counts.filter((voteCount) => voteCount.result_level === 'PARTY') ?? [],
    [region?.vote_counts],
  )

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

  const resultsPageContent = (
    <>
      <PageIndex
        links={[
          {
            label: <><span className="semibold">Telresultaten</span> zoals ze meetellen in de officiele uitslag</>,
            url: '#telresultaten'
          },
          {
            label: <><span className="semibold">Uitleg</span> hoe deze resultaten tot stand zijn gekomen</>,
            url: '#results-timeline'
          },
          {label: <span className="semibold">Hoe u een fout kunt melden</span>, url: '#fout-melden'},
        ]}
      />
      <section id="telresultaten">
        <h3 className="mb-2">Telresultaten</h3>
        <p>
          Het gemeentelijk stembureau heeft de telresultaten van alle stembureaus in {region.region_name} gecontroleerd,
          overgenomen en bij elkaar opgeteld. Hieronder ziet u de telresultaten zoals ze zijn
          opgenomen in het proces-verbaal van de gemeente.
        </p>
      </section>
      <VotesResume type='admittedVoters' votes={region.voter_turnout_counts}/>

      <section className="votes-cast">
        <h4 className="mb-2">Uitgebrachte stemmen</h4>
        <p className="mb-4">Klik op een lijst om de stemmen per kandidaat te zien</p>
        <VotesList voteCounts={partyLevelVoteCounts}/>
      </section>
      <VotesResume type='votesCast' votes={region.voter_turnout_counts}/>
      <ReportsWithResults
        title="Brondocumenten"
        description="Onderstaande documenten bevatten de laatste telresultaten van de gemeente, zoals ze worden meegeteld in de uitslag. De getallen in het overzicht hierboven komen uit het EML_NL tellingbestand."
        documents={region.documents}
      />
    </>
  );

  return (
    <>
      <HtmlHead title={`Resultaten ${municipalityTitle}`}/>
      <div className="page-main page-main-two-columns">
        <div className="page-space-3">
          {hasResults ? (
            resultsPageContent
          ) : (
            <ResultsNotPublished regionLabel={region.region_name}/>
          )}
          <ResultsTimeline
            variant={region.timeline_variant}
            entries={electionConfig.timeline_entries ?? []}
          />
          <IssueNotice issueReportDeadline={electionConfig.issue_report_deadline}/>
        </div>
      </div>
    </>
  )
}
