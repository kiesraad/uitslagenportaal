import { useParams } from 'react-router'
import { Layout } from '../../components/Layout.tsx'
import PageTop from '../../components/PageTop.tsx'
import ResultsNotPublished from '../../components/ResultsPage/ResultsNotPublished.tsx'
import ResultsTimeline from '../../components/ResultsPage/ResultsTimeline.tsx'
import { PageQueryBoundary } from '../../components/PageQueryBoundary.tsx'
import { useElectionConfig, usePartyVoteMatrix, useRegion } from '../../hooks/queries.ts'
import ResultsPageIndex from '../../components/ResultsPage/ResultsPageIndex'
import { appRoutes } from '../../utils/routes.ts'
import IssueNotice from '../../components/ResultsPage/IssueNotice.tsx'
import PartyVoteMatrixTable from '../../components/ResultsPage/PartyVoteMatrixTable.tsx'
import { getRegionLabels } from '../../utils/region.ts'
import { formatDate } from '../../utils/date.ts'
import { getPartyVoteCount } from '../../utils/voteCounts.ts'


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

    const regionLabels = getRegionLabels(electionConfig?.csb_type)
    const partyName = partyVoteMatrix?.party.registered_name ?? partySlug
    const partyListNumber = getPartyVoteCount(region?.vote_counts, partySlug)?.party.list_number

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
                entityLabel={regionLabels.singular}
            />
        )
    }

    const resultsPageContent = (
        <>
            <ResultsPageIndex />
            <section id="telresultaten" className="party-vote-matrix-section">
                <h2 className="text-lg mb-4.5 font-medium">Telresultaten lijst {partyListNumber ?? '-'}</h2>
                <h3 className="party-level-title mb-2">{partyName}</h3>

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
                title={`Telresultaten ${regionLabels.singular} ${region.region_name}\n ${partyName}`}
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
                        variant={region.timeline_variant}
                        entries={electionConfig.timeline_entries ?? []}
                    />
                    <IssueNotice issueReportDeadline={electionConfig.issue_report_deadline} />
                </div>
            </div>
        </Layout>
    )
}
