import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { HomePage } from './pages/HomePage'
import { ElectionConfigMunicipalityListPage } from './pages/ElectionConfigPage/ElectionConfigMunicipalityListPage'
// import { ElectionConfigCSBListPage } from './pages/ElectionConfigPage/ElectionConfigCSBListPage'
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
        <Route path="/:electionConfigSlug/gsb" element={<ElectionConfigMunicipalityListPage />} />
        {/* <Route path="/:electionConfigSlug/csb" element={<ElectionConfigCSBListPage />} /> */}
        <Route path="/:electionConfigSlug/gsb/:regionSlug" element={<MunicipalityPollingstationListPage />} />
        <Route path="/:electionConfigSlug/gsb/:regionSlug/resultaten" element={<MunicipalityResultsPage />} />
        <Route path="/:electionConfigSlug/gsb/:regionSlug/resultaten/:partySlug" element={<MunicipalityPartyResultsPage />} />
        <Route path="/:electionConfigSlug/gsb/:parentRegionSlug/:pollingStationSlug" element={<PollingStationResultsPage />} />
        <Route path="/:electionConfigSlug/gsb/:parentRegionSlug/:pollingStationSlug/:partySlug" element={<PollingStationPartyResultsPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
