export const appRoutes = {
  home: () => '/',
  reportIssue: () => '/fout-melden',
  electionConfigMunicipalityList: (electionConfigSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/gsb`,
  electionConfigCSBList: (electionConfigSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/csb`,
  csbMunicipalityList:  (electionConfigSlug: string, regionSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/csb/${encodeURIComponent(regionSlug)}`,
  csbResults:  (electionConfigSlug: string, regionSlug: string) => `/${encodeURIComponent(electionConfigSlug)}/csb/${encodeURIComponent(regionSlug)}/resultaten`,
  csbPartyResults: (electionConfigSlug: string, regionSlug: string, partySlug: string) =>
    `${appRoutes.csbResults(electionConfigSlug, regionSlug)}/${encodeURIComponent(partySlug)}`,
  municipalityPollingstationList: (electionConfigSlug: string, regionSlug: string, csbSlug?: string) =>
    `/${encodeURIComponent(electionConfigSlug)}/gsb/${encodeURIComponent(regionSlug)}${csbSlug ? `/csb/${encodeURIComponent(csbSlug)}` : ''}`,
  municipalityResults: (electionConfigSlug: string, regionSlug: string, csbSlug?: string) =>
    `${appRoutes.municipalityPollingstationList(electionConfigSlug, regionSlug, csbSlug)}/resultaten`,
  municipalityPartyResults: (electionConfigSlug: string, regionSlug: string, partySlug: string, csbSlug?: string) =>
    `${appRoutes.municipalityResults(electionConfigSlug, regionSlug, csbSlug)}/${encodeURIComponent(partySlug)}`,
  pollingStationResults: (electionConfigSlug: string, regionSlug: string, pollingStationSlug: string, csbSlug?: string) =>
    `${appRoutes.municipalityPollingstationList(electionConfigSlug, regionSlug, csbSlug)}/${encodeURIComponent(pollingStationSlug)}`,
  pollingStationPartyResults: (electionConfigSlug: string, regionSlug: string, pollingStationSlug: string, partySlug: string, csbSlug?: string) =>
    `${appRoutes.pollingStationResults(electionConfigSlug, regionSlug, pollingStationSlug, csbSlug)}/${encodeURIComponent(partySlug)}`
}
