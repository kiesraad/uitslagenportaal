import { useParams } from 'react-router-dom'
import { Layout } from '../../components/Layout'
import PageTop from '../../components/DetailPage/PageTop.tsx'
import SharedTabs from '../../components/DetailPage/SharedTabs.tsx'
import { useElectionConfig, useRegion } from '../../hooks/queries'
import { appRoutes } from '../../utils/routes'
import PollingStationList from '../../components/MunicipalityDetailPage/PollingStationList.tsx'
import './municipality-detail-page.css'

export function MunicipalityDetailPage() {
  const { electionConfigSlug, regionSlug: regionSlugParam } = useParams<{ electionConfigSlug: string; regionSlug: string }>()
  const regionSlug = decodeURIComponent(regionSlugParam ?? '')
  const municipalityDetailRoute = appRoutes.municipalityDetail(electionConfigSlug ?? '', regionSlug)

  const { data: electionConfig } = useElectionConfig(electionConfigSlug)
  const { data: region, isLoading, isError, refetch } = useRegion(electionConfigSlug, regionSlug)

  if (isLoading) {
    return (
      <Layout title="Gemeente laden…" description="Gemeente laden…">
        <p>Gemeente laden…</p>
      </Layout>
    )
  }

  if (isError || !region) {
    return (
      <Layout title="Gemeente niet gevonden" description="Kan gemeente niet laden.">
        <p>Kan gemeente niet laden.</p>
        <button type="button" onClick={() => refetch()}>
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
        subtitle="Geplaatst op: 10 december 2025 - 12:17"
        breadcrumb={[
          { href: appRoutes.home(), label: 'Home' },
          { href: appRoutes.electionConfigDetailMunicipality(electionConfigSlug ?? ''), label: electionConfig?.label ?? 'Verkiezing laden…' },
          { href: municipalityDetailRoute, label: `Gemeente ${region.region_name}` },
        ]}
        tabs={
          <SharedTabs
            tabs={[
              {
                label: 'Resultaten per stembureau',
                value: municipalityDetailRoute,
                activePatterns: [municipalityDetailRoute, `${municipalityDetailRoute}/*`],
              },
              // {
              //   label: 'Hele gemeente',
              //   value: municipalityResultsRoute,
              //   activePatterns: [municipalityResultsRoute],
              // },
            ]}
          />
        }
      />

      <PollingStationList
        region={region}
        electionConfigSlug={electionConfigSlug ?? ''}
        regionSlug={regionSlug}
      />
    </Layout>
  )
}
