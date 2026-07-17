import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { Layout } from '../../components/Layout.tsx'
import PageTop from '../../components/PageTop.tsx'
import SharedTabs from '../../components/SharedTabs.tsx'
import VotesResume from '../../components/ResultsPage/VotesResume.tsx'
import VotesList from '../../components/ResultsPage/VotesList.tsx'
import ReportsWithResults from '../../components/ResultsPage/ReportsWithResults.tsx'
import { useElectionConfig, useRegion } from '../../hooks/queries.ts'
import { appRoutes } from '../../utils/routes.ts'
import IssueNotice from '../../components/ResultsPage/IssueNotice.tsx'
import { getRegionLabel } from '../../utils/region'


export function ElectionConfigCSBResultsPage() {
    const { electionConfigSlug, regionSlug: regionSlugParam } = useParams<{ electionConfigSlug: string; regionSlug: string }>()
    const regionSlug = decodeURIComponent(regionSlugParam ?? '')
    // const municipalityPollingstationListRoute = appRoutes.municipalityPollingstationList(electionConfigSlug ?? '', regionSlug)
    const csbResultsRoute = appRoutes.csbResults(electionConfigSlug ?? '', regionSlug)


    const { data: electionConfig } = useElectionConfig(electionConfigSlug)
    const { data: region, isLoading, isError, refetch } = useRegion(electionConfigSlug, regionSlug)

    const regionLabel = getRegionLabel(electionConfig?.csb_type)

    const partyLevelVoteCounts = useMemo(
        () => region?.vote_counts.filter((voteCount) => voteCount.result_level === 'PARTY') ?? [],
        [region?.vote_counts],
    )

    if (isLoading) {
        return (
            <Layout title={`${regionLabel} laden…`} description={`${regionLabel} laden…`}>

                <p>${regionLabel.toLowerCase()} laden…</p>
            </Layout>
        )
    }

    if (isError || !region) {
        return (
            <Layout title={`${regionLabel} niet gevonden`} description={`Kan ${regionLabel.toLowerCase()} niet laden`}>
                <p>Kan ${regionLabel.toLowerCase()} niet laden.</p>
                <button type="button" onClick={() => refetch()}>
                    Opnieuw proberen
                </button>
            </Layout>
        )
    }

    return (
        <Layout
            title="Resultaten"
        >
            <PageTop
                title={`${regionLabel} ${region.region_name}`}
                subtitle="Geplaatst op: 10 december 2025 - 12:17"
                breadcrumb={[
                    { href: appRoutes.home(), label: 'Home' },
                    { href: appRoutes.electionConfigMunicipalityList(electionConfigSlug ?? ''), label: electionConfig?.label ?? 'Verkiezing laden…' },
                    { href: appRoutes.csbResults(electionConfigSlug ?? '', regionSlug), label: `${regionLabel} ${region.region_name}` },

                ]}
                tabs={
                    <SharedTabs
                        tabs={[
                            {
                                label: 'Heel waterschap',
                                value: csbResultsRoute,
                                activePatterns: [csbResultsRoute],
                            },
                            // {
                            //     label: 'Per gemeente',
                            //     value: municipalityPollingstationListRoute,
                            //     activePatterns: [municipalityPollingstationListRoute],
                            // },
                        ]}
                    />
                }
            />
            <div className="page-main page-main-two-columns">
                <div className="page-space-3">
                    <VotesResume type='admittedVoters' votes={region.voter_turnout_counts} />

                    <section className="votes-cast">
                        <h4 className="mb-2">Uitgebrachte stemmen</h4>
                        <p className="mb-4">Klik op een lijst om de stemmen per kandidaat te zien</p>
                        <VotesList voteCounts={partyLevelVoteCounts} />
                    </section>

                    <VotesResume type='votesCast' votes={region.voter_turnout_counts} />

                    <ReportsWithResults
                        title="Brondocumenten"
                        description={`Onderstaande documenten bevatten de laatste telresultaten van de ${regionLabel.toLowerCase()}, zoals ze worden meegeteld in de uitslag. De getallen in het overzicht hierboven komen uit het EML_NL tellingbestand.`}
                        documents={region.documents}
                    />

                    <IssueNotice />

                </div>
            </div>
        </Layout>
    )
}
