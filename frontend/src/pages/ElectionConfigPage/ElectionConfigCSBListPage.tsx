import { useParams } from 'react-router-dom'
import { Layout } from '../../components/Layout.tsx'
import PageTop from '../../components/PageTop.tsx'
import SharedTabs from '../../components/SharedTabs.tsx'
import { PageQueryBoundary } from '../../components/PageQueryBoundary.tsx'

import { RegionList } from '../../components/ListPage/RegionList.tsx'
import { appRoutes } from '../../utils/routes.ts'
import { useElectionConfig, useRegions } from '../../hooks/queries.ts'
import { getRegionLabels } from '../../utils/region.ts'

export function ElectionConfigCSBListPage() {

  const { electionConfigSlug } = useParams<{ electionConfigSlug: string }>()
  const {
    data: electionConfig,
    isLoading: isElectionLoading,
    isError: isElectionError,
    refetch: refetchElection,
  } = useElectionConfig(electionConfigSlug)
  const {
    data: regions,
    isLoading: isRegionsLoading,
    isError: isRegionsError,
    refetch: refetchRegions,
  } = useRegions(electionConfigSlug, undefined, electionConfig?.csb_type)

  const isLoading = isElectionLoading || isRegionsLoading
  const isError = isElectionError || isRegionsError || !electionConfig || !regions

  if (isLoading || isError) {
    return (
      <PageQueryBoundary
        isLoading={isLoading}
        isError={isError}
        onRetry={() => {
          void refetchElection()
          void refetchRegions()
        }}
        entityLabel="Verkiezing"
      />
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
          { label: getRegionLabels(electionConfig.csb_type).plural, value: appRoutes.electionConfigCSBList(electionConfig.slug), activePatterns: ['/:electionConfigSlug/csb'] },
        ]} />}

      />
      <RegionList
        electionConfig={electionConfig}
        regions={regions}
        regionCategory={electionConfig.csb_type}
      />

    </Layout>
  )
}
