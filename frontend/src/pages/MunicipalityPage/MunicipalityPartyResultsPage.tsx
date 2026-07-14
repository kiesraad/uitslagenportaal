import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { Layout } from '../../components/Layout.tsx'
import PageTop from '../../components/DetailPage/PageTop.tsx'
import { useElectionConfig, useRegion } from '../../hooks/queries.ts'
import { appRoutes } from '../../utils/routes.ts'

import IssueNotice from '../../components/PollingStationDetailPage/IssueNotice'
import CandidatesVoteList from '../../components/DetailPage/CandidatesVoteList'
import PageIndex from '../../components/PageIndex'

export function MunicipalityPartyResultsPage() {
  const {
    electionConfigSlug: electionConfigSlugParam,
    regionSlug: parentRegionSlugParam,
    partySlug: partySlugParam,
  } = useParams<{ electionConfigSlug: string; regionSlug: string; partySlug: string }>()

  const electionConfigSlug = decodeURIComponent(electionConfigSlugParam ?? '')
  const regionSlug = decodeURIComponent(parentRegionSlugParam ?? '')
  const partySlug = decodeURIComponent(partySlugParam ?? '')

  const { data: electionConfig, isLoading: isElectionLoading } = useElectionConfig(electionConfigSlug)
  const { data: region, isLoading: isRegionLoading, isError: isRegionError, refetch } = useRegion(electionConfigSlug, regionSlug)


  const currentPartyVoteCounts = useMemo(
    () =>
      (region?.vote_counts.filter(
        (voteCount) => voteCount.party.slug === partySlug && voteCount.result_level === 'CANDIDATE',
      ) ?? []).sort((a, b) => (a.candidate?.position ?? 0) - (b.candidate?.position ?? 0)),
    [region?.vote_counts, partySlug],
  )

  const partyLevelVoteCounts = useMemo(
    () => region?.vote_counts.filter((voteCount) => voteCount.result_level === 'PARTY') ?? [],
    [region?.vote_counts],
  )

  const partyVoteCount = useMemo(
    () => partyLevelVoteCounts.find((voteCount) => voteCount.party.slug === partySlug),
    [partyLevelVoteCounts, partySlug],
  )

  const partyListNumber = useMemo(
    () => partyLevelVoteCounts.findIndex((voteCount) => voteCount.party.slug === partySlug) + 1,
    [partyLevelVoteCounts, partySlug],
  )

  const municipalityPollingstationListRoute = appRoutes.municipalityPollingstationList(electionConfigSlug, regionSlug)
  const municipalityResultsRoute = appRoutes.municipalityResults(electionConfigSlug, regionSlug)
  const municipalityPartyResultsRoute = `${municipalityResultsRoute}/${encodeURIComponent(partySlug)}`
  const reportHref = appRoutes.reportError(regionSlug)


  const pageTitle = region
    ? `Telresultaten gemeente\n${region.region_name}`
    : 'Telresultaten gemeente'

  if (isElectionLoading || isRegionLoading) {
    return (
      <Layout title="Gemeente laden…" description="Gemeente laden…">
        <p>Gemeente laden…</p>
      </Layout>
    )
  }

  if (isRegionError || !region) {
    return (
      <Layout title="Gemeente niet gevonden" description="Kan gemeente niet laden.">
        <p>Kan gemeente niet laden.</p>
        <button type="button" onClick={() => refetch()}>
          Opnieuw proberen
        </button>
      </Layout>
    )
  }

  if (!region) {
    return (
      <Layout title="Gemeente niet gevonden" description="Gemeente niet gevonden.">
        <p>Gemeente niet gevonden.</p>
      </Layout>
    )
  }

  const partyName = partyVoteCount?.party.registered_name ?? 'Lijst'

  return (
    <Layout
      title={`Telresultaten gemeente – ${region.region_name}`}
      description={`Telresultaten gemeente – ${region.region_name}`}
    >
      <PageTop
        title={pageTitle}
        subtitle="Geplaatst op: 10 december 2025 - 12:17"
        breadcrumb={[
          { href: appRoutes.home(), label: 'Home' },
          { href: appRoutes.electionConfigMunicipalityList(electionConfigSlug), label: electionConfig?.label ?? 'Verkiezing laden…' },
          { href: municipalityPollingstationListRoute, label: `Gemeente ${region.region_name}` },
          { href: municipalityResultsRoute, label: 'Hele gemeente' },
          { href: municipalityPartyResultsRoute, label: partyName },
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
