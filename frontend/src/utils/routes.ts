export const appRoutes = {
  home: () => '/',
  electionConfigDetailMunicipality: (electionConfigSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/gemeente`,
  municipalityDetail: (electionConfigSlug: string, regionSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/${encodeURIComponent(regionSlug)}`,
  pollingStationDetail: (electionConfigSlug: string, regionSlug: string, pollingStationSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/${encodeURIComponent(regionSlug)}/${encodeURIComponent(pollingStationSlug)}`,


  // Below are the pages of the initial stubbed frontend, which we will replace and use as reference
  reportError: (gemeente: string, stembureau?: string) =>
    stembureau
      ? `/gemeente/${encodeURIComponent(gemeente)}/stembureau/resultaten/${encodeURIComponent(stembureau)}/fout-melden`
      : `/gemeente/${encodeURIComponent(gemeente)}/fout-melden`,
}
