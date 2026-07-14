import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { HomePage } from './pages/HomePage'
import { ElectionConfigDetailPage } from './pages/ElectionConfigDetailPage'

import { MunicipalityDetailPollingstationListPage } from './pages/MunicipalityDetailPage/MunicipalityDetailPollingstationListPage.tsx'
import { MunicipalityResultsPage } from './pages/MunicipalityDetailPage/MunicipalityResultsPage.tsx'
import PollingStationResultsPage from './pages/PollingStationResultsPage.tsx'
import PollingStationPartyResultsPage from './pages/PollingStationPartyResultsPage.tsx'


function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/:electionConfigSlug/gemeente" element={<ElectionConfigDetailPage />} />
        <Route path="/:electionConfigSlug/:regionSlug" element={<MunicipalityDetailPollingstationListPage />} />
        <Route path="/:electionConfigSlug/:regionSlug/results" element={<MunicipalityResultsPage />} />
        <Route path="/:electionConfigSlug/:parentRegionSlug/:pollingStationSlug" element={<PollingStationResultsPage />} />
        <Route path="/:electionConfigSlug/:parentRegionSlug/:pollingStationSlug/:partySlug" element={<PollingStationPartyResultsPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
