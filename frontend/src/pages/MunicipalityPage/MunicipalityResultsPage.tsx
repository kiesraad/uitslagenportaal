import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { Layout } from '../../components/Layout.tsx'
import PageTop from '../../components/DetailPage/PageTop.tsx'
import SharedTabs from '../../components/DetailPage/SharedTabs.tsx'
import VotesResume from '../../components/PollingStationDetailPage/VotesResume'
import VotesList from '../../components/DetailPage/VotesList'
import { useElectionConfig, useRegion } from '../../hooks/queries.ts'
import { appRoutes } from '../../utils/routes.ts'

import './municipality-page.css'

export function MunicipalityResultsPage() {
  const { electionConfigSlug, regionSlug: regionSlugParam } = useParams<{ electionConfigSlug: string; regionSlug: string }>()
  const regionSlug = decodeURIComponent(regionSlugParam ?? '')
  const municipalityPollingstationListRoute = appRoutes.municipalityPollingstationList(electionConfigSlug ?? '', regionSlug)
  const municipalityResultsRoute = appRoutes.municipalityResults(electionConfigSlug ?? '', regionSlug)

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

  const partyLevelVoteCounts = useMemo(
    () => region?.vote_counts.filter((voteCount) => voteCount.result_level === 'PARTY') ?? [],
    [region?.vote_counts],
  )

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
          { href: appRoutes.electionConfigMunicipalityList(electionConfigSlug ?? ''), label: electionConfig?.label ?? 'Verkiezing laden…' },
          { href: municipalityPollingstationListRoute, label: `Gemeente ${region.region_name}` },
          
        ]}
        tabs={
          <SharedTabs
            tabs={[
              {
                label: 'Resultaten per stembureau',
                value: municipalityPollingstationListRoute,
                activePatterns: [municipalityPollingstationListRoute],
              },
              {
                label: 'Hele gemeente',
                value: municipalityResultsRoute,
                activePatterns: [municipalityResultsRoute],
              },
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
        </div>
      </div>
    </Layout>
  )
}
