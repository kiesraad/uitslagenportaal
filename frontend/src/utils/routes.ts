export const appRoutes = {
  home: () => '/',
  electionConfigMunicipalityList: (electionConfigSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/gsb`,
  municipalityPollingstationList: (electionConfigSlug: string, regionSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/gsb/${encodeURIComponent(regionSlug)}`,
  municipalityResults: (electionConfigSlug: string, regionSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/gsb/${encodeURIComponent(regionSlug)}/resultaten`,
  municipalityPartyResults: (electionConfigSlug: string, regionSlug: string, partySlug: string) =>
    `${appRoutes.municipalityResults(electionConfigSlug, regionSlug)}/${encodeURIComponent(partySlug)}`,
  pollingStationResults: (electionConfigSlug: string, regionSlug: string, pollingStationSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/gsb/${encodeURIComponent(regionSlug)}/${encodeURIComponent(pollingStationSlug)}`,
  pollingStationPartyResults: (electionConfigSlug: string, regionSlug: string, pollingStationSlug: string, partySlug: string) =>
    `${appRoutes.pollingStationResults(electionConfigSlug, regionSlug, pollingStationSlug)}/${encodeURIComponent(partySlug)}`,


  // Below are the pages of the initial stubbed frontend, which we will replace and use as reference
  reportError: (gemeente: string, stembureau?: string) =>
    stembureau
      ? `/gemeente/${encodeURIComponent(gemeente)}/stembureau/resultaten/${encodeURIComponent(stembureau)}/fout-melden`
      : `/gemeente/${encodeURIComponent(gemeente)}/fout-melden`,
}
