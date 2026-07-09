export const appRoutes = {
  home: () => '/',
  municipalitySearch: () => '/gemeente',
  municipality: (gemeente: string) => `/gemeente/${encodeURIComponent(gemeente)}`,
  municipalityResults: (gemeente: string) => `/gemeente/resultaten/${encodeURIComponent(gemeente)}`,
  municipalityPartyLevel: (gemeente: string, party: string) =>
    `/gemeente/resultaten/${encodeURIComponent(gemeente)}/partij/${encodeURIComponent(party)}`,
  pollingStationResults: (gemeente: string, stembureau: string) =>
    `/gemeente/${encodeURIComponent(gemeente)}/stembureau/resultaten/${encodeURIComponent(stembureau)}`,
  partyLevel: (gemeente: string, stembureau: string, party: string) =>
    `/gemeente/${encodeURIComponent(gemeente)}/stembureau/resultaten/${encodeURIComponent(stembureau)}/partij/${encodeURIComponent(party)}`,
  reportError: (gemeente: string, stembureau?: string) =>
    stembureau
      ? `/gemeente/${encodeURIComponent(gemeente)}/stembureau/resultaten/${encodeURIComponent(stembureau)}/fout-melden`
      : `/gemeente/${encodeURIComponent(gemeente)}/fout-melden`,
  kieskring: (kieskring: string) => `/kieskring/${encodeURIComponent(kieskring)}`,
  kieskringGemeente: (kieskring: string) => `/kieskring/${encodeURIComponent(kieskring)}/gemeente`,
  nederland: (nederland = '') => nederland ? `/nederland/${encodeURIComponent(nederland)}` : '/nederland',
  nederlandList: (listNumber: string | number, list: string) =>
    `/nederland/lijst/${encodeURIComponent(String(listNumber))}/${encodeURIComponent(list)}`,
  nederlandCandidate: (listNumber: string | number, list: string, candidate: string) =>
    `/nederland/lijst/${encodeURIComponent(String(listNumber))}/${encodeURIComponent(list)}/kandidaat/${encodeURIComponent(candidate)}`,
}
