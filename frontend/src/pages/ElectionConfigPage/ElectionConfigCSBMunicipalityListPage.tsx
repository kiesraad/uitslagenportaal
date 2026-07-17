import { useParams } from 'react-router-dom'
import { Layout } from '../../components/Layout.tsx'
import PageTop from '../../components/PageTop.tsx'
import SharedTabs from '../../components/SharedTabs.tsx'

import { RegionList } from '../../components/ListPage/RegionList.tsx'
import { appRoutes } from '../../utils/routes.ts'
import { useElectionConfig, useRegions, useRegion } from '../../hooks/queries.ts'
import { getRegionLabel } from '../../utils/region.ts'

export function ElectionConfigCSBMunicipalityListPage() {

    const { electionConfigSlug } = useParams<{ electionConfigSlug: string }>()
    const { regionSlug } = useParams<{ regionSlug: string }>()
    
    const { data: electionConfig, isLoading, isError, refetch: refetch } = useElectionConfig(electionConfigSlug)
    const { data: region } = useRegion(electionConfigSlug, regionSlug)
    
    const { data: regions } = useRegions(electionConfigSlug, regionSlug, 'GEMEENTE', true)
    
    const electionLabel = electionConfig?.label ?? 'Verkiezing laden…'
    const regionLabel = getRegionLabel(electionConfig?.csb_type)

    const csbResultsRoute = appRoutes.csbResults(electionConfigSlug ?? '', regionSlug ?? '')
    const csbMunicipalityListRoute = appRoutes.csbMunicipalityList(electionConfigSlug ?? '', regionSlug ?? '')


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
                title={`${regionLabel} ${region?.region_name}`}
                subtitle="Geplaatst op: 10 december 2025 - 12:17"
                breadcrumb={[
                    { href: appRoutes.home(), label: 'Home' },
                    { href: appRoutes.electionConfigMunicipalityList(electionConfigSlug ?? ''), label: electionConfig?.label ?? 'Verkiezing laden…' },
                    { href: appRoutes.csbResults(electionConfigSlug ?? '', regionSlug ?? ''), label: `${regionLabel} ${region?.region_name}` },

                ]}
                tabs={
                    <SharedTabs
                        tabs={[
                            {
                                label: 'Heel waterschap',
                                value: csbResultsRoute,
                                activePatterns: [csbResultsRoute],
                            },
                            {
                                label: 'Per gemeente',
                                value: csbMunicipalityListRoute,
                                activePatterns: [csbMunicipalityListRoute],
                            },
                        ]}
                    />
                }
            />
            <RegionList
                electionConfig={electionConfig}
                regions={regions}
                regionCategory='GEMEENTE'
            />

        </Layout>
    )
}
