import { useParams } from 'react-router-dom'
import { Layout } from '../../components/Layout.tsx'
import PageTop from '../../components/PageTop.tsx'
import ResultsNotPublished from '../../components/ResultsPage/ResultsNotPublished.tsx'
import ResultsTimeline from '../../components/ResultsPage/ResultsTimeline.tsx'
import { PageQueryBoundary } from '../../components/PageQueryBoundary.tsx'
import { useElectionConfig, usePartyVoteMatrix, useRegion } from '../../hooks/queries.ts'
import PageIndex from '../../components/PageIndex'
import { appRoutes } from '../../utils/routes.ts'
import IssueNotice from '../../components/ResultsPage/IssueNotice.tsx'
import PartyVoteMatrixTable from '../../components/ResultsPage/PartyVoteMatrixTable.tsx'
import { getRegionLabel } from '../../utils/region.ts'
import { formatDate } from '../../utils/date.ts'


export function CSBPartyResultsPage() {
    const {
        electionConfigSlug,
        regionSlug: regionSlugParam,
        partySlug: partySlugParam,
    } = useParams<{ electionConfigSlug: string; regionSlug: string, partySlug: string }>()
    const regionSlug = decodeURIComponent(regionSlugParam ?? '')
    const partySlug = decodeURIComponent(partySlugParam ?? '')

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
    const {
        data: partyVoteMatrix,
        isLoading: isPartyVoteMatrixLoading,
        isError: isPartyVoteMatrixError,
        refetch: refetchPartyVoteMatrix,
    } = usePartyVoteMatrix(region?.election_slug, regionSlug, partySlug)

    const regionLabel = getRegionLabel(electionConfig?.csb_type) || 'Regio'
    const partyName = partyVoteMatrix?.party.registered_name ?? partySlug

    const isLoading = isElectionLoading || isRegionLoading || isPartyVoteMatrixLoading
    const isError = isElectionError || isRegionError || isPartyVoteMatrixError || !electionConfig || !region || !partyVoteMatrix

    const hasResults = (partyVoteMatrix?.rows.length ?? 0) > 0

    if (isLoading || isError) {
        return (
            <PageQueryBoundary
                isLoading={isLoading}
                isError={isError}
                onRetry={() => {
                    void refetchElection()
                    void refetchRegion()
                    void refetchPartyVoteMatrix()
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
            <section id="telresultaten" className="party-vote-matrix-section">
                <h3 className="mb-2">Telresultaten</h3>
                <h3 className="mb-2"><span className="bold">{partyName}</span></h3>

                <p className="mb-4">
                    Het centraal stembureau heeft de telresultaten van alle gemeenten en kieskringen gecontroleerd, overgenomen en bij elkaar opgeteld.
                    Hieronder ziet u de telresultaten zoals ze zijn opgenmomen in het proces-verbaal van het centraal stembureau.
                </p>
                <PartyVoteMatrixTable matrix={partyVoteMatrix} />
            </section>
        </>
    )

    return (
        <Layout
            title="Resultaten"
        >
            <PageTop
                title={`Telresultaten ${regionLabel} ${region.region_name}\n ${partyName}`}
                subtitle={`Geplaatst op: ${formatDate(region.results_available_at)}`}
                breadcrumb={[
                    { href: appRoutes.home(), label: 'Home' },
                    { href: appRoutes.electionConfigMunicipalityList(electionConfigSlug ?? ''), label: electionConfig.label },
                    { href: appRoutes.csbResults(electionConfigSlug ?? '', regionSlug), label: region.region_name },
                    { href: appRoutes.csbPartyResults(electionConfigSlug ?? '', regionSlug, partySlug), label: partyName },
                ]}
            />
            <div className="page-main page-main-two-columns">
                <div className="page-space-3 party-vote-matrix-page">
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
