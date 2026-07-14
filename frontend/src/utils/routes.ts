export const appRoutes = {
  home: () => '/',
  electionConfigMunicipalityList: (electionConfigSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/gemeente`,
  municipalityPollingstationList: (electionConfigSlug: string, regionSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/${encodeURIComponent(regionSlug)}`,
  municipalityResults: (electionConfigSlug: string, regionSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/${encodeURIComponent(regionSlug)}/results`,
  pollingStationResults: (electionConfigSlug: string, regionSlug: string, pollingStationSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/${encodeURIComponent(regionSlug)}/${encodeURIComponent(pollingStationSlug)}`,


  // Below are the pages of the initial stubbed frontend, which we will replace and use as reference
  reportError: (gemeente: string, stembureau?: string) =>
    stembureau
      ? `/gemeente/${encodeURIComponent(gemeente)}/stembureau/resultaten/${encodeURIComponent(stembureau)}/fout-melden`
      : `/gemeente/${encodeURIComponent(gemeente)}/fout-melden`,
}
