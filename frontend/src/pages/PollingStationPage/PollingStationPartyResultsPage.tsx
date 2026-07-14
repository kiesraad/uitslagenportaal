import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import IssueNotice from '../../components/ResultsPage/IssueNotice'
import PageTop from '../../components/PageTop'
import CandidatesVoteList from '../../components/ResultsPage/CandidatesVoteList'
import { Layout } from '../../components/Layout'
import { useElectionConfig, useRegion } from '../../hooks/queries'
import { appRoutes } from '../../utils/routes'
import PageIndex from '../../components/PageIndex'

export default function PollingStationPartyResultsPage() {
  const {
    electionConfigSlug: electionConfigSlugParam,
    parentRegionSlug: parentRegionSlugParam,
    pollingStationSlug: pollingStationSlugParam,
    partySlug: partySlugParam,
  } = useParams<{ electionConfigSlug: string; parentRegionSlug: string; pollingStationSlug: string; partySlug: string }>()

  const electionConfigSlug = decodeURIComponent(electionConfigSlugParam ?? '')
  const parentRegionSlug = decodeURIComponent(parentRegionSlugParam ?? '')
  const pollingStationSlug = decodeURIComponent(pollingStationSlugParam ?? '')
  const partySlug = decodeURIComponent(partySlugParam ?? '')

  const { data: electionConfig, isLoading: isElectionLoading } = useElectionConfig(electionConfigSlug)
  const { data: region, isLoading: isRegionLoading, isError: isRegionError, refetch } = useRegion(electionConfigSlug, parentRegionSlug)
  const { data: pollingStation, isLoading: isPollingStationLoading } = useRegion(electionConfigSlug, pollingStationSlug)


  const currentPartyVoteCounts = useMemo(
    () =>
      (pollingStation?.vote_counts.filter(
        (voteCount) => voteCount.party.slug === partySlug && voteCount.result_level === 'CANDIDATE',
      ) ?? []).sort((a, b) => (a.candidate?.position ?? 0) - (b.candidate?.position ?? 0)),
    [pollingStation?.vote_counts, partySlug],
  )

  const partyLevelVoteCounts = useMemo(
    () => pollingStation?.vote_counts.filter((voteCount) => voteCount.result_level === 'PARTY') ?? [],
    [pollingStation?.vote_counts],
  )

  const partyVoteCount = useMemo(
    () => partyLevelVoteCounts.find((voteCount) => voteCount.party.slug === partySlug),
    [partyLevelVoteCounts, partySlug],
  )

  const partyListNumber = useMemo(
    () => partyLevelVoteCounts.findIndex((voteCount) => voteCount.party.slug === partySlug) + 1,
    [partyLevelVoteCounts, partySlug],
  )

  const municipalityPollingstationListRoute = appRoutes.municipalityPollingstationList(electionConfigSlug, parentRegionSlug)
  const pollingStationResultsRoute = appRoutes.pollingStationResults(electionConfigSlug, parentRegionSlug, pollingStationSlug)
  const pollingStationPartyResultsRoute = appRoutes.pollingStationPartyResults(electionConfigSlug, parentRegionSlug, pollingStationSlug, partySlug)
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

  const partyName = partyVoteCount?.party.registered_name ?? 'Lijst'

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
          { href: appRoutes.electionConfigMunicipalityList(electionConfigSlug), label: electionConfig?.label ?? 'Verkiezing laden…' },
          { href: municipalityPollingstationListRoute, label: `Gemeente ${region.region_name}` },
          { href: pollingStationResultsRoute, label: pollingStation.region_name },
          { href: pollingStationPartyResultsRoute, label: partyName },
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
            <h2 className="result-how-title mb-0 semibold">Telresultaten lijst {partyListNumber || '?'}</h2>
            <h3 className="party-level-title mb-2">{partyName}</h3>
            <CandidatesVoteList
              voteCounts={currentPartyVoteCounts}
              partyVote={partyVoteCount}
              partyListNumber={partyListNumber}
            />
          </section>

          <IssueNotice id="fout-melden" reportHref={reportHref} />
        </div>
      </div>
    </Layout>
  )
}
