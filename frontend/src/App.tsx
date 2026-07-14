import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { HomePage } from './pages/HomePage'
import { ElectionConfigDetailPage } from './pages/ElectionConfigDetailPage'

import { MunicipalityDetailPollingstationListPage } from './pages/MunicipalityDetailPage/MunicipalityDetailPollingstationListPage.tsx'
import PollingStationDetailPage from './pages/PollingStationDetailPage'
import PollingStationPartyDetailPage from './pages/PollingStationPartyDetailPage'


function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/:electionConfigSlug/gemeente" element={<ElectionConfigDetailPage />} />
        <Route path="/:electionConfigSlug/:regionSlug" element={<MunicipalityDetailPollingstationListPage />} />
        <Route path="/:electionConfigSlug/:parentRegionSlug/:pollingStationSlug" element={<PollingStationDetailPage />} />
        <Route path="/:electionConfigSlug/:parentRegionSlug/:pollingStationSlug/:partySlug" element={<PollingStationPartyDetailPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
