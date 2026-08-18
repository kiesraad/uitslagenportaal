import { useParams } from 'react-router'
import { Layout } from '../../components/Layout.tsx'
import PageTop from '../../components/PageTop.tsx'
import { PageQueryBoundary } from '../../components/PageQueryBoundary.tsx'
import { useElectionConfig, useRegion } from '../../hooks/queries.ts'
import { appRoutes } from '../../utils/routes.ts'
import PartyCandidatesResultsContent from '../../components/ResultsPage/PartyCandidatesResultsContent.tsx'
import { formatDate } from '../../utils/date.ts'
import { getCsbCrumb } from '../../utils/region.ts'
import { getPartyVoteCount } from '../../utils/voteCounts.ts'

export function MunicipalityPartyResultsPage() {
  const {
    electionConfigSlug: electionConfigSlugParam,
    regionSlug: parentRegionSlugParam,
    partySlug: partySlugParam,
    csbSlug: csbSlugParam,
  } = useParams<{ electionConfigSlug: string; regionSlug: string; partySlug: string; csbSlug?: string }>()

  const electionConfigSlug = decodeURIComponent(electionConfigSlugParam ?? '')
  const regionSlug = decodeURIComponent(parentRegionSlugParam ?? '')
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
  } = useRegion(electionConfigSlug, regionSlug, csbSlug)

  const isLoading = isElectionLoading || isRegionLoading
  const isError = isElectionError || isRegionError || !electionConfig || !region

  const municipalityResultsRoute = appRoutes.municipalityResults(electionConfigSlug, regionSlug, csbSlug)
  const municipalityPartyResultsRoute = appRoutes.municipalityPartyResults(electionConfigSlug, regionSlug, partySlug, csbSlug)

  if (isLoading || isError) {
    return (
      <PageQueryBoundary
        isLoading={isLoading}
        isError={isError}
        onRetry={() => {
          void refetchElection()
          void refetchRegion()
        }}
        entityLabel="Gemeente"
      />
    )
  }

  const partyName = getPartyVoteCount(region.vote_counts, partySlug)?.party.registered_name ?? 'Lijst'
  const pageTitle = `Telresultaten gemeente\n${region.region_name}`

  return (
    <Layout
      title={`Telresultaten gemeente – ${region.region_name}`}
      description={`Telresultaten gemeente – ${region.region_name}`}
    >
      <PageTop
        title={pageTitle}
        subtitle={`Geplaatst op: ${formatDate(region.results_available_at)}`}
        breadcrumb={[
          { href: appRoutes.home(), label: 'Home' },
          { href: appRoutes.electionConfigMunicipalityList(electionConfigSlug), label: electionConfig.label },
          getCsbCrumb(region, electionConfigSlug),
          { href: municipalityResultsRoute, label: `Gemeente ${region.region_name}` },
          { href: municipalityPartyResultsRoute, label: partyName },
        ]}
      />
      <div className="page-main page-main-two-columns">
        <div className="page-space-3">
          <PartyCandidatesResultsContent
            voteCounts={region.vote_counts}
            partySlug={partySlug}
            issueReportDeadline={electionConfig.issue_report_deadline}
          />
        </div>
      </div>
    </Layout>
  )
}
