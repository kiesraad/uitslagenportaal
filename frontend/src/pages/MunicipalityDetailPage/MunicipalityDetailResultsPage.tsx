import { useParams } from 'react-router-dom'
import { Layout } from '../../components/Layout.tsx'
import PageTop from '../../components/DetailPage/PageTop.tsx'
import SharedTabs from '../../components/DetailPage/SharedTabs.tsx'
import VotesResume from '../../components/PollingStationDetailPage/VotesResume'
import type { VoterTurnoutCount } from '../../api/types'
import { useElectionConfig, useRegion } from '../../hooks/queries.ts'
import { appRoutes } from '../../utils/routes.ts'

import './municipality-detail-page.css'

export function MunicipalityDetailResultsPage() {
  const { electionConfigSlug, regionSlug: regionSlugParam } = useParams<{ electionConfigSlug: string; regionSlug: string }>()
  const regionSlug = decodeURIComponent(regionSlugParam ?? '')
  const municipalityDetailPollingstationListRoute = appRoutes.municipalityDetailPollingstationList(electionConfigSlug ?? '', regionSlug)
  const municipalityDetailResultsRoute = appRoutes.municipalityDetailResultsRoute(electionConfigSlug ?? '', regionSlug)

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

  type VoterTurnoutRow = { reason_code: string; label: string; bold?: boolean }

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

  return (
    <Layout
      title="Resultaten"
      description="Resultaten per stembureau"
    >
      <PageTop
        title={`Gemeente ${region.region_name}`}
        subtitle="Geplaatst op: 10 december 2025 - 12:17"
        breadcrumb={[
          { href: appRoutes.home(), label: 'Home' },
          { href: appRoutes.electionConfigDetailMunicipality(electionConfigSlug ?? ''), label: electionConfig?.label ?? 'Verkiezing laden…' },
          { href: municipalityDetailPollingstationListRoute, label: `Gemeente ${region.region_name}` },
        ]}
        tabs={
          <SharedTabs
            tabs={[
              {
                label: 'Resultaten per stembureau',
                value: municipalityDetailPollingstationListRoute,
                activePatterns: [municipalityDetailPollingstationListRoute],
              },
              {
                label: 'Hele gemeente',
                value: municipalityDetailResultsRoute,
                activePatterns: [municipalityDetailResultsRoute],
              },
            ]}
          />
        }
      />
      <div className="page-main page-main-two-columns">
        <div className="page-space-3">
          <section className="admitted-voters">
            <h4 className="mb-2">Toegelaten kiezers</h4>
            <VotesResume votes={getAdmittedVoterVotes(region.voter_turnout_counts, ADMITTED_VOTER_ROWS)} />
          </section>

          <VotesResume
            votes={getAdmittedVoterVotes(region.voter_turnout_counts, VOTES_CAST)}
          />
        </div>
      </div>
    </Layout>
  )
}
