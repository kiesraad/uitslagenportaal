import { useParams } from 'react-router-dom'
import { Layout } from '../../components/Layout.tsx'
import PageTop from '../../components/PageTop.tsx'
import SharedTabs from '../../components/SharedTabs.tsx'
import { useElectionConfig, useRegion } from '../../hooks/queries.ts'
import { appRoutes } from '../../utils/routes.ts'
import { useRegions } from '../../hooks/queries.ts'
import { RegionList } from '../../components/ListPage/RegionList.tsx'
import { formatDate } from '../../utils/date.ts'


export function MunicipalityPollingstationListPage() {
  const { electionConfigSlug, regionSlug: regionSlugParam } = useParams<{ electionConfigSlug: string; regionSlug: string }>()
  const regionSlug = decodeURIComponent(regionSlugParam ?? '')
  const municipalityPollingstationListRoute = appRoutes.municipalityPollingstationList(electionConfigSlug ?? '', regionSlug)
  const municipalityResultsRoute = appRoutes.municipalityResults(electionConfigSlug ?? '', regionSlug)

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
  } = useRegion(electionConfigSlug, regionSlug)
  const { data: pollingStations } = useRegions(electionConfigSlug, regionSlug, 'STEMBUREAU')

  if (isElectionConfigLoading || isRegionLoading) {
    return (
      <Layout title="Gemeente laden…" description="Gemeente laden…">
        <p>Gemeente laden…</p>
      </Layout>
    )
  }

  if (isElectionConfigError || isRegionError || !electionConfig || !region) {
    return (
      <Layout title="Gemeente niet gevonden" description="Kan gemeente niet laden.">
        <p>Kan gemeente niet laden.</p>
        <button type="button" onClick={() => {
          refetchElectionConfig()
          refetchRegion()
        }}>
          Opnieuw proberen
        </button>
      </Layout>
    )
  }

  return (
    <Layout
      title="Resultaten per stembureau"
      description="Resultaten per stembureau"
    >
      <PageTop
        title={`Gemeente ${region.region_name}`}
        subtitle={`Geplaatst op: ${formatDate(region.results_available_at)}`}
        breadcrumb={[
          { href: appRoutes.home(), label: 'Home' },
          { href: appRoutes.electionConfigMunicipalityList(electionConfigSlug ?? ''), label: electionConfig.label },
          { href: municipalityPollingstationListRoute, label: `Gemeente ${region.region_name}` },
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
        regionCategory='STEMBUREAU'
      />

    </Layout>
  )
}
