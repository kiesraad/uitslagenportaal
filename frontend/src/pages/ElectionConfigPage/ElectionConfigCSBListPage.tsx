import { useParams } from 'react-router-dom'
import { Layout } from '../../components/Layout.tsx'
import PageTop from '../../components/PageTop.tsx'
import SharedTabs from '../../components/SharedTabs.tsx'

import { RegionList } from '../../components/ListPage/RegionList.tsx'
import { appRoutes } from '../../utils/routes.ts'
import { useElectionConfig, useRegions } from '../../hooks/queries.ts'
import { getRegionLabel } from '../../utils/region.ts'

export function ElectionConfigCSBListPage() {

  const { electionConfigSlug } = useParams<{ electionConfigSlug: string }>()
  const { data: electionConfig, isLoading, isError, refetch } = useElectionConfig(electionConfigSlug)
  const { data: regions } = useRegions(electionConfigSlug, undefined, electionConfig?.csb_type)

  const electionLabel = electionConfig?.label ?? 'Verkiezing laden…'

  if (isLoading) {
    return (
      <Layout title={electionLabel} description="Telresultaten laden…">
        <p>Verkiezing laden…</p>
      </Layout>
    )
  }

  if (isError || !electionConfig) {
    return (
      <Layout title="Verkiezing niet gevonden" description="Kan verkiezing niet laden.">
        <p>Kan verkiezing niet laden.</p>
        <button type="button" onClick={() => refetch()}>
          Opnieuw proberen
        </button>
      </Layout>
    )
  }

  return (
    <Layout
      title={`Telresultaten ${electionConfig.label}`}
      description={`Bekijk de telresultaten per gemeente van de ${electionConfig.label}.`}
    >
      <PageTop
        title={`Telresultaten ${electionConfig.label}`}
        subtitle={`Verkiezingsdag: ${electionConfig.date ? new Date(electionConfig.date).toLocaleDateString('nl-NL', { year: 'numeric', month: 'long', day: 'numeric' }) : ''}`}
        breadcrumb={[
          { href: '/', label: 'Home' },
          { href: appRoutes.electionConfigMunicipalityList(electionConfigSlug ?? ''), label: electionConfig.label },
        ]}
        tabs={<SharedTabs tabs={[
          { label: 'Gemeente', value: appRoutes.electionConfigMunicipalityList(electionConfig.slug), activePatterns: ['/:electionConfigSlug/gsb'] },
          { label: getRegionLabel(electionConfig.csb_type, true), value: appRoutes.electionConfigCSBList(electionConfig.slug), activePatterns: ['/:electionConfigSlug/csb'] },
        ]} />}

      />
      <RegionList
        electionConfig={electionConfig}
        regions={regions}
        regionCategory='WATERSCHAP'
      />

    </Layout>
  )
}
