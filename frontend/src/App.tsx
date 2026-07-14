import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { HomePage } from './pages/HomePage'
import { ElectionConfigMunicipalityListPage } from './pages/ElectionConfigMunicipalityListPage'
import { MunicipalityPollingstationListPage } from './pages/MunicipalityPage/MunicipalityPollingstationListPage'
import { MunicipalityPartyResultsPage } from './pages/MunicipalityPage/MunicipalityPartyResultsPage'
import { MunicipalityResultsPage } from './pages/MunicipalityPage/MunicipalityResultsPage'
import PollingStationResultsPage from './pages/PollingStationPage/PollingStationResultsPage.tsx'
import PollingStationPartyResultsPage from './pages/PollingStationPage/PollingStationPartyResultsPage.tsx'



function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/:electionConfigSlug/gemeente" element={<ElectionConfigMunicipalityListPage />} />
        <Route path="/:electionConfigSlug/:regionSlug" element={<MunicipalityPollingstationListPage />} />
        <Route path="/:electionConfigSlug/:regionSlug/results" element={<MunicipalityResultsPage />} />
        <Route path="/:electionConfigSlug/:regionSlug/results/:partySlug" element={<MunicipalityPartyResultsPage />} />
        <Route path="/:electionConfigSlug/:parentRegionSlug/:pollingStationSlug" element={<PollingStationResultsPage />} />
        <Route path="/:electionConfigSlug/:parentRegionSlug/:pollingStationSlug/:partySlug" element={<PollingStationPartyResultsPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
