import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import IssueNotice from '../../components/ResultsPage/IssueNotice'
import PageTop from '../../components/PageTop'
import VotesList from '../../components/ResultsPage/VotesList'
import VotesResume from '../../components/ResultsPage/VotesResume'
import { Layout } from '../../components/Layout'
import { PageQueryBoundary } from '../../components/PageQueryBoundary'
import { useElectionConfig, useRegion } from '../../hooks/queries'
import { appRoutes } from '../../utils/routes'
import PageIndex from '../../components/PageIndex'
import ResultsTimeline from '../../components/ResultsPage/ResultsTimeline'
import { formatDate } from '../../utils/date'
import { getCsbCrumb } from '../../utils/region'


export default function PollingStationResultsPage() {
  const {
    electionConfigSlug: electionConfigSlugParam,
    parentRegionSlug: parentRegionSlugParam,
    pollingStationSlug: pollingStationSlugParam,
    csbSlug: csbSlugParam,
  } = useParams<{ electionConfigSlug: string; parentRegionSlug: string; pollingStationSlug: string; csbSlug?: string }>()

  const electionConfigSlug = decodeURIComponent(electionConfigSlugParam ?? '')
  const parentRegionSlug = decodeURIComponent(parentRegionSlugParam ?? '')
  const pollingStationSlug = decodeURIComponent(pollingStationSlugParam ?? '')
  const csbSlug = csbSlugParam ? decodeURIComponent(csbSlugParam) : undefined

  const {
    data: electionConfig,
    isLoading: isElectionLoading,
    isError: isElectionError,
    refetch: refetchElection,
  } = useElectionConfig(electionConfigSlug)
  const {
    data: region,
    isLoading: isRegionLoading,
    isError: isRegionError,
    refetch: refetchRegion,
  } = useRegion(electionConfigSlug, parentRegionSlug, csbSlug)
  const {
    data: pollingStation,
    isLoading: isPollingStationLoading,
    isError: isPollingStationError,
    refetch: refetchPollingStation,
  } = useRegion(electionConfigSlug, pollingStationSlug, csbSlug, parentRegionSlug)

  const isLoading = isElectionLoading || isRegionLoading || isPollingStationLoading
  const isError =
    isElectionError ||
    isRegionError ||
    isPollingStationError ||
    !electionConfig ||
    !region ||
    !pollingStation

  const partyLevelVoteCounts = useMemo(
    () => pollingStation?.vote_counts.filter((voteCount) => voteCount.result_level === 'PARTY') ?? [],
    [pollingStation?.vote_counts],
  )

  const municipalityPollingstationListRoute = appRoutes.municipalityPollingstationList(electionConfigSlug, parentRegionSlug, csbSlug)
  const pollingStationResultsRoute = appRoutes.pollingStationResults(electionConfigSlug, parentRegionSlug, pollingStationSlug, csbSlug)

  if (isLoading || isError) {
    return (
      <PageQueryBoundary
        isLoading={isLoading}
        isError={isError}
        onRetry={() => {
          void refetchElection()
          void refetchRegion()
          void refetchPollingStation()
        }}
        entityLabel="Stembureau"
      />
    )
  }

  const pageTitle = `Telresultaten stembureau\n${pollingStation.region_name}`

  return (
    <Layout
      title={`Telresultaten stembureau – ${pollingStation.region_name}`}
      description={`Telresultaten stembureau – ${pollingStation.region_name}`}
    >
      <PageTop
        title={pageTitle}
        subtitle={`Geplaatst op: ${formatDate(region.results_available_at)}`}
        breadcrumb={[
          { href: appRoutes.home(), label: 'Home' },
          { href: appRoutes.electionConfigMunicipalityList(electionConfigSlug), label: electionConfig.label },
          getCsbCrumb(region, electionConfigSlug),
          { href: municipalityPollingstationListRoute, label: `Gemeente ${region.region_name}` },
          { href: pollingStationResultsRoute, label: pollingStation.region_name },
        ]}
      />
      <div className="page-main page-main-two-columns">
        <div className="page-space-3">
          <PageIndex
            links={[
              { label: <><span className="font-semibold">Telresultaten</span> zoals ze meetellen in de officiele uitslag</>, url: '#telresultaten' },
              { label: <><span className="font-semibold">Uitleg</span> hoe deze resultaten tot stand zijn gekomen</>, url: '#results-timeline' },
              { label: <span className="font-semibold">Hoe u een fout kunt melden</span>, url: '#fout-melden' },
            ]}
          />

          <section id="telresultaten">
            <h3 className="mb-2">Telresultaten</h3>
            <p>De gemeente typt de telgegevens van alle stembureaus over in de uitslagensoftware. Zo kunnen alle stemmen worden opgeteld. Hieronder zie je hoe de gegevens van dit stembureau zijn overgenomen in de uitslagensoftware.</p>
          </section>

          <VotesResume type='admittedVoters' votes={pollingStation.voter_turnout_counts} />

          <section className="votes-cast">
            <h4 className="mb-2">Uitgebrachte stemmen</h4>
            <p className="mb-4">Klik op een lijst om de stemmen per kandidaat te zien</p>
            <VotesList voteCounts={partyLevelVoteCounts} />
          </section>

          <VotesResume
            type='votesCast'
            votes={pollingStation.voter_turnout_counts}
          />

          <ResultsTimeline
            variant={pollingStation.timeline_variant}
            entries={pollingStation.timeline_entries ?? []}
          />

          <IssueNotice issueReportDeadline={electionConfig.issue_report_deadline} />
        </div>
      </div>
    </Layout>
  )
}
