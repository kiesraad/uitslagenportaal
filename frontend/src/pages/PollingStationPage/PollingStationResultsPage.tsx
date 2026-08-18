import { useParams } from 'react-router'
import PageTop from '../../components/PageTop'
import RegionResultsContent from '../../components/ResultsPage/RegionResultsContent'
import { Layout } from '../../components/Layout'
import { PageQueryBoundary } from '../../components/PageQueryBoundary'
import { useElectionConfig, useRegion } from '../../hooks/queries'
import { appRoutes } from '../../utils/routes'
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
          <RegionResultsContent
            intro="De gemeente typt de telgegevens van alle stembureaus over in de uitslagensoftware. Zo kunnen alle stemmen worden opgeteld. Hieronder zie je hoe de gegevens van dit stembureau zijn overgenomen in de uitslagensoftware."
            voteCounts={pollingStation.vote_counts}
            turnoutVotes={pollingStation.voter_turnout_counts}
            timelineVariant={pollingStation.timeline_variant}
            timelineEntries={pollingStation.timeline_entries ?? []}
            issueReportDeadline={electionConfig.issue_report_deadline}
          />
        </div>
      </div>
    </Layout>
  )
}
