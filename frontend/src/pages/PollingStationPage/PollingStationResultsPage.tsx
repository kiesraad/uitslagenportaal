import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import IssueNotice from '../../components/PollingStationDetailPage/IssueNotice'
import PageTop from '../../components/DetailPage/PageTop'
import VotesList from '../../components/DetailPage/VotesList'
import VotesResume from '../../components/PollingStationDetailPage/VotesResume'
import { Layout } from '../../components/Layout'
import { useElectionConfig, useRegion } from '../../hooks/queries'
import { appRoutes } from '../../utils/routes'
import PageIndex from '../../components/PageIndex'


export default function PollingStationResultsPage() {
  const {
    electionConfigSlug: electionConfigSlugParam,
    parentRegionSlug: parentRegionSlugParam,
    pollingStationSlug: pollingStationSlugParam,
  } = useParams<{ electionConfigSlug: string; parentRegionSlug: string; pollingStationSlug: string }>()

  const electionConfigSlug = decodeURIComponent(electionConfigSlugParam ?? '')
  const parentRegionSlug = decodeURIComponent(parentRegionSlugParam ?? '')
  const pollingStationSlug = decodeURIComponent(pollingStationSlugParam ?? '')

  const { data: electionConfig, isLoading: isElectionLoading } = useElectionConfig(electionConfigSlug)
  const { data: region, isLoading: isRegionLoading, isError: isRegionError, refetch } = useRegion(electionConfigSlug, parentRegionSlug)
  const { data: pollingStation, isLoading: isPollingStationLoading } = useRegion(electionConfigSlug, pollingStationSlug)

  const partyLevelVoteCounts = useMemo(
    () => pollingStation?.vote_counts.filter((voteCount) => voteCount.result_level === 'PARTY') ?? [],
    [pollingStation?.vote_counts],
  )

  const municipalityDetailPollingstationListRoute = appRoutes.municipalityDetailPollingstationList(electionConfigSlug, parentRegionSlug)
  const pollingStationDetailRoute = appRoutes.pollingStationDetail(electionConfigSlug, parentRegionSlug, pollingStationSlug)
  const reportHref = appRoutes.reportError(parentRegionSlug, pollingStationSlug)

  const pageTitle = pollingStation
    ? `Telresultaten stembureau\n${pollingStation.region_name}`
    : 'Telresultaten stembureau'

  if (isElectionLoading || isRegionLoading || isPollingStationLoading) {
    return (
      <Layout title="Stembureau laden…" description="Stembureau laden…">
        <p>Stembureau laden…</p>
      </Layout>
    )
  }

  if (isRegionError || !region) {
    return (
      <Layout title="Stembureau niet gevonden" description="Kan stembureau niet laden.">
        <p>Kan stembureau niet laden.</p>
        <button type="button" onClick={() => refetch()}>
          Opnieuw proberen
        </button>
      </Layout>
    )
  }

  if (!pollingStation) {
    return (
      <Layout title="Stembureau niet gevonden" description="Stembureau niet gevonden.">
        <p>Stembureau niet gevonden.</p>
      </Layout>
    )
  }

  return (
    <Layout
      title={`Telresultaten stembureau – ${pollingStation.region_name}`}
      description={`Telresultaten stembureau – ${pollingStation.region_name}`}
    >
      <PageTop
        title={pageTitle}
        subtitle="Geplaatst op: 10 december 2025 - 12:17"
        breadcrumb={[
          { href: appRoutes.home(), label: 'Home' },
          { href: appRoutes.electionConfigDetailMunicipality(electionConfigSlug), label: electionConfig?.label ?? 'Verkiezing laden…' },
          { href: municipalityDetailPollingstationListRoute, label: `Gemeente ${region.region_name}` },
          { href: pollingStationDetailRoute, label: pollingStation.region_name },
        ]}
      />
      <div className="page-main page-main-two-columns">
        <div className="page-space-3">
          <PageIndex
            links={[
              { label: <><span className="bold">Telresultaten</span> zoals ze meetellen in de officiele uitslag</>, url: '#telresultaten' },
              { label: <span className="bold">Hoe u een fout kunt melden</span>, url: '#fout-melden' },
            ]}
          />

          <section id="telresultaten">
            <h3 className="mb-2">Telresultaten</h3>
            <p>De gemeente typt de telgegevens van alle stembureaus over in de uitslagensoftware. Zo kunnen alle stemmen worden opgeteld. Hieronder zie je hoe de gegevens van dit stembureau zijn overgenomen in de uitslagensoftware.</p>
          </section>

          <VotesResume type='admittedVoters' votes={pollingStation.voter_turnout_counts} />

          <section className="votes-cast">
            <h4 className="mb-2">Uitgebrachte stemmen</h4>
            <p className="mb-4">Klik op een lijst om de stemmen per kandidaat te zien</p>
            <VotesList voteCounts={partyLevelVoteCounts} />
          </section>

          <VotesResume
            type='votesCast'
            votes={pollingStation.voter_turnout_counts}
          />
          <IssueNotice id="fout-melden" reportHref={reportHref} />
        </div>
      </div>
    </Layout>
  )
}
