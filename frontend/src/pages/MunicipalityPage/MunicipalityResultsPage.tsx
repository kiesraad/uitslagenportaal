import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { Layout } from '../../components/Layout.tsx'
import PageTop from '../../components/PageTop.tsx'
import SharedTabs from '../../components/SharedTabs.tsx'
import VotesResume from '../../components/ResultsPage/VotesResume.tsx'
import VotesList from '../../components/ResultsPage/VotesList.tsx'
import ReportsWithResults from '../../components/ResultsPage/ReportsWithResults.tsx'
import ResultsNotPublished from '../../components/ResultsPage/ResultsNotPublished.tsx'
import ResultsTimeline from '../../components/ResultsPage/ResultsTimeline'
import { useElectionConfig, useRegion } from '../../hooks/queries.ts'
import { appRoutes } from '../../utils/routes.ts'
import IssueNotice from '../../components/ResultsPage/IssueNotice.tsx'
import { formatDate } from '../../utils/date.ts'
import { getCsbCrumb } from '../../utils/region.ts'


export function MunicipalityResultsPage() {
  const { electionConfigSlug, regionSlug: regionSlugParam, csbSlug: csbSlugParam } = useParams<{ electionConfigSlug: string; regionSlug: string; csbSlug?: string }>()
  const regionSlug = decodeURIComponent(regionSlugParam ?? '')
  const csbSlug = csbSlugParam ? decodeURIComponent(csbSlugParam) : undefined
  const municipalityPollingstationListRoute = appRoutes.municipalityPollingstationList(electionConfigSlug ?? '', regionSlug, csbSlug)
  const municipalityResultsRoute = appRoutes.municipalityResults(electionConfigSlug ?? '', regionSlug, csbSlug)

  const { data: electionConfig } = useElectionConfig(electionConfigSlug)
  const { data: region, isLoading, isError, refetch } = useRegion(electionConfigSlug, regionSlug, csbSlug)

  const hasResults = Array.isArray(region?.vote_counts) && region.vote_counts.length > 0

  const partyLevelVoteCounts = useMemo(
    () => region?.vote_counts.filter((voteCount) => voteCount.result_level === 'PARTY') ?? [],
    [region?.vote_counts],
  )

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

  const municipalityTitle = region.region_name

  const resultsPageContent = (
    <>
      <VotesResume type='admittedVoters' votes={region.voter_turnout_counts} />

      <section className="votes-cast">
        <h4 className="mb-2">Uitgebrachte stemmen</h4>
        <p className="mb-4">Klik op een lijst om de stemmen per kandidaat te zien</p>
        <VotesList voteCounts={partyLevelVoteCounts} />
      </section>
      <VotesResume type='votesCast' votes={region.voter_turnout_counts} />
      <ReportsWithResults
        title="Brondocumenten"
        description="Onderstaande documenten bevatten de laatste telresultaten van de gemeente, zoals ze worden meegeteld in de uitslag. De getallen in het overzicht hierboven komen uit het EML_NL tellingbestand."
        documents={region.documents}
      />
    </>
  );


  return (
    <Layout
      title="Resultaten"
      description="Resultaten per stembureau"
    >
      <PageTop
        title={municipalityTitle}
        subtitle={`Geplaatst op: ${formatDate(region.results_available_at)}`}
        breadcrumb={[
          { href: appRoutes.home(), label: 'Home' },
          { href: appRoutes.electionConfigMunicipalityList(electionConfigSlug ?? ''), label: electionConfig?.label ?? 'Verkiezing laden…' },
          getCsbCrumb(region, electionConfigSlug ?? ''),
          { href: municipalityPollingstationListRoute, label: municipalityTitle },

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
          {!hasResults ? (
            <ResultsNotPublished regionLabel={region.region_name} />
          ) : (
            resultsPageContent
          )}
          <ResultsTimeline
            title="Hoe komt de uitslag tot stand?"
            description="TBD."
            entries={electionConfig?.timeline_entries ?? []}
          />
          <IssueNotice />
        </div>
      </div>
    </Layout>
  )
}
