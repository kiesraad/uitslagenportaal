import { Navigate, useParams } from 'react-router-dom'
import { Layout } from '../../components/Layout.tsx'
import PageTop from '../../components/PageTop.tsx'
import SharedTabs from '../../components/SharedTabs.tsx'
import { PageQueryBoundary } from '../../components/PageQueryBoundary.tsx'
import { useElectionConfig, useRegion } from '../../hooks/queries.ts'
import { appRoutes } from '../../utils/routes.ts'
import { useRegions } from '../../hooks/queries.ts'
import { RegionList } from '../../components/ListPage/RegionList.tsx'
import { formatDate } from '../../utils/date.ts'
import { getCsbCrumb } from '../../utils/region.ts'


export function MunicipalityPollingstationListPage() {
  const { electionConfigSlug, regionSlug: regionSlugParam, csbSlug: csbSlugParam } = useParams<{ electionConfigSlug: string; regionSlug: string; csbSlug?: string }>()
  const regionSlug = decodeURIComponent(regionSlugParam ?? '')
  const csbSlug = csbSlugParam ? decodeURIComponent(csbSlugParam) : undefined
  const municipalityPollingstationListRoute = appRoutes.municipalityPollingstationList(electionConfigSlug ?? '', regionSlug, csbSlug)
  const municipalityResultsRoute = appRoutes.municipalityResults(electionConfigSlug ?? '', regionSlug, csbSlug)

  const {
    data: electionConfig,
    isLoading: isElectionConfigLoading,
    isError: isElectionConfigError,
    refetch: refetchElectionConfig,
  } = useElectionConfig(electionConfigSlug)
  const {
    data: region,
    isLoading: isRegionLoading,
    isError: isRegionError,
    refetch: refetchRegion,
  } = useRegion(electionConfigSlug, regionSlug, csbSlug)
  const {
    data: pollingStations,
    isLoading: isPollingStationsLoading,
    isError: isPollingStationsError,
    refetch: refetchPollingStations,
  } = useRegions(electionConfigSlug, regionSlug, 'STEMBUREAU', false, csbSlug)

  const isLoading = isElectionConfigLoading || isRegionLoading || isPollingStationsLoading
  const isError =
    isElectionConfigError ||
    isRegionError ||
    isPollingStationsError ||
    !electionConfig ||
    !region ||
    !pollingStations

  if (isLoading || isError) {
    return (
      <PageQueryBoundary
        isLoading={isLoading}
        isError={isError}
        onRetry={() => {
          void refetchElectionConfig()
          void refetchRegion()
          void refetchPollingStations()
        }}
        entityLabel="Gemeente"
      />
    )
  }

  const hasResults = Array.isArray(region.vote_counts) && region.vote_counts.length > 0
  if (!hasResults) {
    return <Navigate to={municipalityResultsRoute} replace />
  }

  const municipalityTitle = `Gemeente ${region.region_name}`

  return (
    <Layout
      title="Resultaten per stembureau"
      description="Resultaten per stembureau"
    >
      <PageTop
        title={municipalityTitle}
        subtitle={`Geplaatst op: ${formatDate(region.results_available_at)}`}
        breadcrumb={[
          { href: appRoutes.home(), label: 'Home' },
          { href: appRoutes.electionConfigMunicipalityList(electionConfigSlug ?? ''), label: electionConfig.label },
          getCsbCrumb(region, electionConfigSlug ?? ''),
          { href: municipalityPollingstationListRoute, label: municipalityTitle },
        ]}
        tabs={
          <SharedTabs
            tabs={[
              {
                label: 'Resultaten per stembureau',
                value: municipalityPollingstationListRoute,
                activePatterns: [municipalityPollingstationListRoute],
              },
              {
                label: 'Hele gemeente',
                value: municipalityResultsRoute,
                activePatterns: [municipalityResultsRoute],
              },
            ]}
          />
        }
      />
      <RegionList
        electionConfig={electionConfig}
        regions={pollingStations}
        parentRegionSlug={regionSlug}
        parentCsbSlug={csbSlug}
        regionTitle={municipalityTitle}
        regionCategory='STEMBUREAU'
      />

    </Layout>
  )
}
