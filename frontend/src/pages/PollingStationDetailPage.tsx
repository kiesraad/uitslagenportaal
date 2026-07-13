import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import IssueNotice from '../components/PollingStationDetailPage/IssueNotice'
import PageTop from '../components/DetailPage/PageTop'
import VotesList from '../components/DetailPage/VotesList'
import VotesResume from '../components/PollingStationDetailPage/VotesResume'
import ResultsTimeline from '../components/PollingStationDetailPage/ResultsTimeline'
import { Layout } from '../components/Layout'
import { useElectionConfig, useRegion } from '../hooks/queries'
import { appRoutes } from '../utils/routes'
import PageIndex from '../components/PageIndex'
import type { VoterTurnoutCount } from '../api/types'


type VoterTurnoutRow = { reason_code: string; label: string; bold?: boolean }


export default function PollingStationDetailPage() {
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

  const municipalityDetailRoute = appRoutes.municipalityDetail(electionConfigSlug, parentRegionSlug)
  const pollingStationDetailRoute = appRoutes.pollingStationDetail(electionConfigSlug, parentRegionSlug, pollingStationSlug)
  const reportHref = appRoutes.reportError(parentRegionSlug, pollingStationSlug)

  const ADMITTED_VOTER_ROWS: VoterTurnoutRow[] = [
    { reason_code: 'geldige stempassen', label: 'Stempassen' },
    { reason_code: 'geldige volmachtbewijzen', label: 'Volmachtbewijzen' },
    { reason_code: 'geldige kiezerspassen', label: 'Kiezerspassen' },
    { reason_code: 'toegelaten kiezers', label: 'Toegelaten kiezers', bold: true },
  ]


  const VOTES_CAST: VoterTurnoutRow[] = [
    { reason_code: 'total counted', label: 'Totaal stemmen op kandidaten', bold: true },
    { reason_code: 'blanco', label: 'Blanco stemmen' },
    { reason_code: 'ongeldig', label: 'Ongeldige stemmen' },
    { reason_code: 'cast', label: 'Totaal uitgebrachte stemmen' },
  ]


  function getAdmittedVoterVotes(voterTurnoutCounts: VoterTurnoutCount[] | undefined, rows: VoterTurnoutRow[]) {
    return rows.map(({ reason_code, label, bold }) => ({
      name: label,
      count: voterTurnoutCounts?.find((entry) => entry.reason_code === reason_code)?.votes ?? 0,
      ...(bold ? { bold: true as const } : {}),
    }))
  }

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
          { href: municipalityDetailRoute, label: `Gemeente ${region.region_name}` },
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

          <section className="admitted-voters">
            <h4 className="mb-2">Toegelaten kiezers</h4>
            <VotesResume votes={getAdmittedVoterVotes(pollingStation.voter_turnout_counts, ADMITTED_VOTER_ROWS)} />
          </section>

          <section className="votes-cast">
            <h4 className="mb-2">Uitgebrachte stemmen</h4>
            <p className="mb-4">Klik op een lijst om de stemmen per kandidaat te zien</p>
            <VotesList voteCounts={partyLevelVoteCounts} />
          </section>

          <ResultsTimeline
            title="Hoe komt de uitslag tot stand?"
            entries={pollingStation.timeline_entries ?? []}
          />

          <VotesResume
            votes={getAdmittedVoterVotes(pollingStation.voter_turnout_counts, VOTES_CAST)}
          />
          <IssueNotice id="fout-melden" reportHref={reportHref} />
        </div>
      </div>
    </Layout>
  )
}
