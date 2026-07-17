export const appRoutes = {
  home: () => '/',
  electionConfigMunicipalityList: (electionConfigSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/gsb`,
  electionConfigCSBList: (electionConfigSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/csb`,
  csbMunicipalityList:  (electionConfigSlug: string, regionSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/csb/${encodeURIComponent(regionSlug)}`,
  csbResults:  (electionConfigSlug: string, regionSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/csb/${encodeURIComponent(regionSlug)}/resultaten`,
  municipalityPollingstationList: (electionConfigSlug: string, regionSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/gsb/${encodeURIComponent(regionSlug)}`,
  municipalityResults: (electionConfigSlug: string, regionSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/gsb/${encodeURIComponent(regionSlug)}/resultaten`,
  municipalityPartyResults: (electionConfigSlug: string, regionSlug: string, partySlug: string) =>
    `${appRoutes.municipalityResults(electionConfigSlug, regionSlug)}/${encodeURIComponent(partySlug)}`,
  pollingStationResults: (electionConfigSlug: string, regionSlug: string, pollingStationSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/gsb/${encodeURIComponent(regionSlug)}/${encodeURIComponent(pollingStationSlug)}`,
  pollingStationPartyResults: (electionConfigSlug: string, regionSlug: string, pollingStationSlug: string, partySlug: string) =>
    `${appRoutes.pollingStationResults(electionConfigSlug, regionSlug, pollingStationSlug)}/${encodeURIComponent(partySlug)}`
}
