import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { HomePage } from './pages/HomePage'
import { ElectionConfigDetailPage } from './pages/ElectionConfigDetailPage'

import { MunicipalityPollingstationListPage } from './pages/MunicipalityDetailPage/MunicipalityPollingstationListPage'
import { MunicipalityResultsPage } from './pages/MunicipalityDetailPage/MunicipalityResultsPage'
import PollingStationResultsPage from './pages/PollingStationResultsPage.tsx'
import PollingStationPartyResultsPage from './pages/PollingStationPartyResultsPage'


function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/:electionConfigSlug/gemeente" element={<ElectionConfigDetailPage />} />
        <Route path="/:electionConfigSlug/:regionSlug" element={<MunicipalityPollingstationListPage />} />
        <Route path="/:electionConfigSlug/:regionSlug/results" element={<MunicipalityResultsPage />} />
        <Route path="/:electionConfigSlug/:parentRegionSlug/:pollingStationSlug" element={<PollingStationResultsPage />} />
        <Route path="/:electionConfigSlug/:parentRegionSlug/:pollingStationSlug/:partySlug" element={<PollingStationPartyResultsPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
