import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import IssueNotice from '../../components/ResultsPage/IssueNotice'
import PageTop from '../../components/PageTop'
import CandidatesVoteList from '../../components/ResultsPage/CandidatesVoteList'
import { Layout } from '../../components/Layout'
import { PageQueryBoundary } from '../../components/PageQueryBoundary'
import { useElectionConfig, useRegion } from '../../hooks/queries'
import { appRoutes } from '../../utils/routes'
import ResultsPageIndex from '../../components/ResultsPage/ResultsPageIndex'
import { formatDate } from '../../utils/date'
import { getCsbCrumb } from '../../utils/region'
import { getCandidateVoteCountsForParty, getPartyVoteCount } from '../../utils/voteCounts'

export default function PollingStationPartyResultsPage() {
  const {
    electionConfigSlug: electionConfigSlugParam,
    parentRegionSlug: parentRegionSlugParam,
    pollingStationSlug: pollingStationSlugParam,
    partySlug: partySlugParam,
    csbSlug: csbSlugParam,
  } = useParams<{ electionConfigSlug: string; parentRegionSlug: string; pollingStationSlug: string; partySlug: string; csbSlug?: string }>()

  const electionConfigSlug = decodeURIComponent(electionConfigSlugParam ?? '')
  const parentRegionSlug = decodeURIComponent(parentRegionSlugParam ?? '')
  const pollingStationSlug = decodeURIComponent(pollingStationSlugParam ?? '')
  const partySlug = decodeURIComponent(partySlugParam ?? '')
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

  const currentPartyVoteCounts = useMemo(
    () => getCandidateVoteCountsForParty(pollingStation?.vote_counts, partySlug),
    [pollingStation?.vote_counts, partySlug],
  )

  const partyVoteCount = useMemo(
    () => getPartyVoteCount(pollingStation?.vote_counts, partySlug),
    [pollingStation?.vote_counts, partySlug],
  )

  const partyListNumber = partyVoteCount?.party.list_number

  const municipalityPollingstationListRoute = appRoutes.municipalityPollingstationList(electionConfigSlug, parentRegionSlug, csbSlug)
  const pollingStationResultsRoute = appRoutes.pollingStationResults(electionConfigSlug, parentRegionSlug, pollingStationSlug, csbSlug)
  const pollingStationPartyResultsRoute = appRoutes.pollingStationPartyResults(electionConfigSlug, parentRegionSlug, pollingStationSlug, partySlug, csbSlug)

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

  const partyName = partyVoteCount?.party.registered_name ?? 'Lijst'
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
          { href: municipalityPollingstationListRoute, label: region.region_name },
          { href: pollingStationResultsRoute, label: pollingStation.region_name },
          { href: pollingStationPartyResultsRoute, label: partyName },
        ]}
      />
      <div className="page-main page-main-two-columns">
        <div className="page-space-3">
          <ResultsPageIndex variant="party" />

          <section id="telresultaten">
            <h2 className="text-lg mb-4.5 font-medium">Telresultaten lijst {partyListNumber ?? '-'}</h2>
            <h3 className="party-level-title mb-2">{partyName}</h3>
            <CandidatesVoteList
              voteCounts={currentPartyVoteCounts}
              partyVote={partyVoteCount}
              partyListNumber={partyListNumber}
            />
          </section>

          <IssueNotice issueReportDeadline={electionConfig.issue_report_deadline} />
        </div>
      </div>
    </Layout>
  )
}
