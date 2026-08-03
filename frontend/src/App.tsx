import {BrowserRouter, Route, Routes} from 'react-router-dom'
import {HomePage} from './pages/HomePage'
import {ElectionConfigMunicipalityListPage} from './pages/ElectionConfigPage/ElectionConfigMunicipalityListPage'
import {ElectionConfigCSBListPage} from './pages/ElectionConfigPage/ElectionConfigCSBListPage'
import {CSBResultsPage} from './pages/CSBPage/CSBResultsPage.tsx'
import {CSBPartyResultsPage} from './pages/CSBPage/CSBPartyResultsPage.tsx'
import {CSBMunicipalityListPage} from './pages/CSBPage/CSBMunicipalityListPage.tsx'
import {MunicipalityPollingstationListPage} from './pages/MunicipalityPage/MunicipalityPollingstationListPage'
import {MunicipalityPartyResultsPage} from './pages/MunicipalityPage/MunicipalityPartyResultsPage'
import {MunicipalityResultsPage} from './pages/MunicipalityPage/MunicipalityResultsPage'
import PollingStationResultsPage from './pages/PollingStationPage/PollingStationResultsPage.tsx'
import PollingStationPartyResultsPage from './pages/PollingStationPage/PollingStationPartyResultsPage.tsx'
import MunicipalityPageLayout from "@/pages/MunicipalityPage/MunicipalityPageLayout.tsx";


function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/:electionConfigSlug/csb" element={<ElectionConfigCSBListPage />} />
        <Route path="/:electionConfigSlug/csb/:regionSlug" element={<CSBMunicipalityListPage />} />
        <Route path="/:electionConfigSlug/csb/:regionSlug/resultaten" element={<CSBResultsPage />} />
        <Route path="/:electionConfigSlug/csb/:regionSlug/resultaten/:partySlug" element={<CSBPartyResultsPage />} />
        <Route path="/:electionConfigSlug/gsb" element={<ElectionConfigMunicipalityListPage />} />
        <Route path="/:electionConfigSlug/gsb/:regionSlug/csb/:csbSlug" element={<MunicipalityPageLayout />}>
          <Route index element={<MunicipalityPollingstationListPage />} />
          <Route path="resultaten" element={<MunicipalityResultsPage />} />
        </Route>
        <Route path="/:electionConfigSlug/gsb/:regionSlug/csb/:csbSlug/resultaten/:partySlug" element={<MunicipalityPartyResultsPage />} />
        <Route path="/:electionConfigSlug/gsb/:parentRegionSlug/csb/:csbSlug/:pollingStationSlug" element={<PollingStationResultsPage />} />
        <Route path="/:electionConfigSlug/gsb/:parentRegionSlug/csb/:csbSlug/:pollingStationSlug/:partySlug" element={<PollingStationPartyResultsPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
