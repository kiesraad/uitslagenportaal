import {BrowserRouter, Route, Routes} from 'react-router-dom'
import {HomePage} from './pages/HomePage'
import {ReportIssuePage} from './pages/ReportIssuePage'
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
import { appRoutes } from './utils/routes.ts'


function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage/>}/>
        <Route path={appRoutes.reportIssue()} element={<ReportIssuePage/>}/>
        <Route path="/:electionConfigSlug">
          <Route path="csb" element={<ElectionConfigCSBListPage/>}/>
          <Route path="csb/:regionSlug" element={<CSBMunicipalityListPage/>}/>
          <Route path="csb/:regionSlug/resultaten" element={<CSBResultsPage/>}/>
          <Route path="csb/:regionSlug/resultaten/:partySlug" element={<CSBPartyResultsPage/>}/>
          <Route path="gsb" element={<ElectionConfigMunicipalityListPage/>}/>
          <Route path="gsb/:regionSlug/csb/:csbSlug" element={<MunicipalityPageLayout/>}>
            <Route index element={<MunicipalityPollingstationListPage/>}/>
            <Route path="resultaten" element={<MunicipalityResultsPage/>}/>
          </Route>
          <Route path="gsb/:regionSlug/csb/:csbSlug/resultaten/:partySlug" element={<MunicipalityPartyResultsPage/>}/>
          <Route path="gsb/:parentRegionSlug/csb/:csbSlug/:pollingStationSlug" element={<PollingStationResultsPage/>}/>
          <Route path="gsb/:parentRegionSlug/csb/:csbSlug/:pollingStationSlug/:partySlug"
                 element={<PollingStationPartyResultsPage/>}/>
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
