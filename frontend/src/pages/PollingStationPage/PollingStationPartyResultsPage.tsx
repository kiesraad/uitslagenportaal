import { useParams } from 'react-router'
import PageTop from '../../components/PageTop'
import PartyCandidatesResultsContent from '../../components/ResultsPage/PartyCandidatesResultsContent'
import { Layout } from '../../components/Layout'
import { PageQueryBoundary } from '../../components/PageQueryBoundary'
import { useElectionConfig, useRegion } from '../../hooks/queries'
import { appRoutes } from '../../utils/routes'
import { formatDate } from '../../utils/date'
import { getCsbCrumb } from '../../utils/region'
import { getPartyVoteCount } from '../../utils/voteCounts'

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

  const partyName = getPartyVoteCount(pollingStation.vote_counts, partySlug)?.party.registered_name ?? 'Lijst'
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
          <PartyCandidatesResultsContent
            voteCounts={pollingStation.vote_counts}
            partySlug={partySlug}
            issueReportDeadline={electionConfig.issue_report_deadline}
          />
        </div>
      </div>
    </Layout>
  )
}
