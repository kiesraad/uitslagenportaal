import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { Layout } from '../../components/Layout.tsx'
import PageTop from '../../components/PageTop.tsx'
import SharedTabs from '../../components/SharedTabs.tsx'
import VotesResume from '../../components/ResultsPage/VotesResume.tsx'
import VotesList from '../../components/ResultsPage/VotesList.tsx'
import ReportsWithResults from '../../components/ResultsPage/ReportsWithResults.tsx'
import ResultsNotPublished from '../../components/ResultsPage/ResultsNotPublished.tsx'
import ResultsTimeline from '../../components/ResultsPage/ResultsTimeline.tsx'
import { PageQueryBoundary } from '../../components/PageQueryBoundary.tsx'
import { useElectionConfig, useRegion } from '../../hooks/queries.ts'
import PageIndex from '../../components/PageIndex'
import { appRoutes } from '../../utils/routes.ts'
import IssueNotice from '../../components/ResultsPage/IssueNotice.tsx'
import { getRegionLabel } from '../../utils/region.ts'
import { formatDate } from '../../utils/date.ts'


export function CSBResultsPage() {
    const { electionConfigSlug, regionSlug: regionSlugParam } = useParams<{ electionConfigSlug: string; regionSlug: string }>()
    const regionSlug = decodeURIComponent(regionSlugParam ?? '')
    const csbResultsRoute = appRoutes.csbResults(electionConfigSlug ?? '', regionSlug)
    const csbMunicipalityListRoute = appRoutes.csbMunicipalityList(electionConfigSlug ?? '', regionSlug)

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
    } = useRegion(electionConfigSlug, regionSlug)

    const regionLabel = getRegionLabel(electionConfig?.csb_type) || 'Regio'

    const isLoading = isElectionLoading || isRegionLoading
    const isError = isElectionError || isRegionError || !electionConfig || !region

    const hasResults = Array.isArray(region?.vote_counts) && region.vote_counts.length > 0

    const partyLevelVoteCounts = useMemo(
        () => region?.vote_counts.filter((voteCount) => voteCount.result_level === 'PARTY') ?? [],
        [region?.vote_counts],
    )

    if (isLoading || isError) {
        return (
            <PageQueryBoundary
                isLoading={isLoading}
                isError={isError}
                onRetry={() => {
                    void refetchElection()
                    void refetchRegion()
                }}
                entityLabel={regionLabel}
            />
        )
    }

    const resultsPageContent = (
        <>
            <PageIndex
                links={[
                    { label: <><span className="bold">Telresultaten</span> zoals ze meetellen in de officiele uitslag</>, url: '#telresultaten' },
                    { label: <><span className="bold">Uitleg</span> hoe deze resultaten tot stand zijn gekomen</>, url: '#results-timeline' },
                    { label: <span className="bold">Hoe u een fout kunt melden</span>, url: '#fout-melden' },
                ]}
            />
            <section id="telresultaten">
                <h3 className="mb-2">Telresultaten</h3>
                <p>
                    Het hoofdstembureau heeft de telresultaten van alle gemeentes in {region.region_name} gecontroleerd,
                    overgenomen en bij elkaar opgeteld. Hieronder ziet u de telresultaten zoals ze zijn
                    opgenomen in het proces-verbaal van het hoofdstembureau.
                </p>
            </section>
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
        </>
    )

    return (
        <Layout
            title="Resultaten"
        >
            <PageTop
                title={region.region_name}
                subtitle={`Geplaatst op: ${formatDate(region.results_available_at)}`}
                breadcrumb={[
                    { href: appRoutes.home(), label: 'Home' },
                    { href: appRoutes.electionConfigMunicipalityList(electionConfigSlug ?? ''), label: electionConfig.label },
                    { href: appRoutes.csbResults(electionConfigSlug ?? '', regionSlug), label: region.region_name },
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
            <div className="page-main page-main-two-columns">
                <div className="page-space-3">
                    {!hasResults ? (
                        <ResultsNotPublished regionLabel={region.region_name} />
                    ) : (
                        resultsPageContent
                    )}
                    <ResultsTimeline
                        title="Hoe komt de uitslag tot stand?"
                        description="TBD."
                        entries={electionConfig.timeline_entries ?? []}
                    />
                    <IssueNotice />
                </div>
            </div>
        </Layout>
    )
}
