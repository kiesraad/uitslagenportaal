import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import IssueNotice from '../../components/ResultsPage/IssueNotice'
import PageTop from '../../components/PageTop'
import VotesList from '../../components/ResultsPage/VotesList'
import VotesResume from '../../components/ResultsPage/VotesResume'
import { Layout } from '../../components/Layout'
import { useElectionConfig, useRegion } from '../../hooks/queries'
import { appRoutes } from '../../utils/routes'
import PageIndex from '../../components/PageIndex'
import ResultsTimeline from '../../components/ResultsPage/ResultsTimeline'
import { formatDate } from '../../utils/date'
import { getCsbCrumb } from '../../utils/region'


export default function PollingStationResultsPage() {
  const {
    electionConfigSlug: electionConfigSlugParam,
    parentRegionSlug: parentRegionSlugParam,
    pollingStationSlug: pollingStationSlugParam,
    csbSlug: csbSlugParam,
  } = useParams<{ electionConfigSlug: string; parentRegionSlug: string; pollingStationSlug: string; csbSlug?: string }>()

  const electionConfigSlug = decodeURIComponent(electionConfigSlugParam ?? '')
  const parentRegionSlug = decodeURIComponent(parentRegionSlugParam ?? '')
  const pollingStationSlug = decodeURIComponent(pollingStationSlugParam ?? '')
  const csbSlug = csbSlugParam ? decodeURIComponent(csbSlugParam) : undefined

  const { data: electionConfig, isLoading: isElectionLoading } = useElectionConfig(electionConfigSlug)
  const { data: region, isLoading: isRegionLoading, isError: isRegionError, refetch } = useRegion(electionConfigSlug, parentRegionSlug, csbSlug)
  const { data: pollingStation, isLoading: isPollingStationLoading } = useRegion(electionConfigSlug, pollingStationSlug)

  const partyLevelVoteCounts = useMemo(
    () => pollingStation?.vote_counts.filter((voteCount) => voteCount.result_level === 'PARTY') ?? [],
    [pollingStation?.vote_counts],
  )

  const municipalityPollingstationListRoute = appRoutes.municipalityPollingstationList(electionConfigSlug, parentRegionSlug, csbSlug)
  const pollingStationResultsRoute = appRoutes.pollingStationResults(electionConfigSlug, parentRegionSlug, pollingStationSlug, csbSlug)

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
        subtitle={`Geplaatst op: ${formatDate(region.results_available_at)}`}
        breadcrumb={[
          { href: appRoutes.home(), label: 'Home' },
          { href: appRoutes.electionConfigMunicipalityList(electionConfigSlug), label: electionConfig?.label ?? 'Verkiezing laden…' },
          getCsbCrumb(region, electionConfigSlug),
          { href: municipalityPollingstationListRoute, label: region.region_name },
          { href: pollingStationResultsRoute, label: pollingStation.region_name },
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

          <ResultsTimeline
            title="Hoe komt de uitslag tot stand?"
            description="Het stembureau doet een sneltelling per partij. Het gemeentelijk stembureau telt de volgende dag alles nog een keer na en telt de stemmen per kandidaat op een centrale tellocatie. Die telresultaten staan in het verslag van het gemeentelijk stembureau/stembureau voor het openbaar lichaam."
            entries={pollingStation.timeline_entries ?? []}
          />

          <IssueNotice />
        </div>
      </div>
    </Layout>
  )
}
