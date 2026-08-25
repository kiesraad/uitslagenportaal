import { useQueryClient } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router";
import MunicipalityPageLayout from "@/pages/MunicipalityPage/MunicipalityPageLayout.tsx";
import { useScrollToTop } from "./hooks/useScrollToTop.ts";
import { CSBMunicipalityListPage } from "./pages/CSBPage/CSBMunicipalityListPage.tsx";
import { CSBPartyResultsPage } from "./pages/CSBPage/CSBPartyResultsPage.tsx";
import { CSBResultsPage } from "./pages/CSBPage/CSBResultsPage.tsx";
import { ElectionConfigCSBListPage, electionConfigLoader } from "./pages/ElectionConfigPage/ElectionConfigCSBListPage";
import { ElectionConfigMunicipalityListPage } from "./pages/ElectionConfigPage/ElectionConfigMunicipalityListPage";
import { HomePage } from "./pages/HomePage";
import { MunicipalityPartyResultsPage } from "./pages/MunicipalityPage/MunicipalityPartyResultsPage";
import { MunicipalityPollingstationListPage } from "./pages/MunicipalityPage/MunicipalityPollingstationListPage";
import { MunicipalityResultsPage } from "./pages/MunicipalityPage/MunicipalityResultsPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import PollingStationPartyResultsPage from "./pages/PollingStationPage/PollingStationPartyResultsPage.tsx";
import PollingStationResultsPage from "./pages/PollingStationPage/PollingStationResultsPage.tsx";
import { ReportIssuePage } from "./pages/ReportIssuePage";

function ScrollToTop() {
   useScrollToTop();
   return null;
}

function App() {
   const queryClient = useQueryClient();
   return (
      <BrowserRouter>
         <ScrollToTop />
         <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/:electionConfigSlug" loader={electionConfigLoader(queryClient)}>
               <Route index element={<NotFoundPage />} />
               <Route path="fout-melden" element={<ReportIssuePage />} />
               <Route path="csb" element={<ElectionConfigCSBListPage />} />
               <Route path="csb/:regionSlug" element={<CSBMunicipalityListPage />} />
               <Route path="csb/:regionSlug/resultaten" element={<CSBResultsPage />} />
               <Route path="csb/:regionSlug/resultaten/:partySlug" element={<CSBPartyResultsPage />} />
               <Route path="gsb" element={<ElectionConfigMunicipalityListPage />} />
               <Route path="gsb/:regionSlug/csb/:csbSlug" element={<MunicipalityPageLayout />}>
                  <Route index element={<MunicipalityPollingstationListPage />} />
                  <Route path="resultaten" element={<MunicipalityResultsPage />} />
               </Route>
               <Route
                  path="gsb/:regionSlug/csb/:csbSlug/resultaten/:partySlug"
                  element={<MunicipalityPartyResultsPage />}
               />
               <Route
                  path="gsb/:parentRegionSlug/csb/:csbSlug/:pollingStationSlug"
                  element={<PollingStationResultsPage />}
               />
               <Route
                  path="gsb/:parentRegionSlug/csb/:csbSlug/:pollingStationSlug/:partySlug"
                  element={<PollingStationPartyResultsPage />}
               />
               <Route path="*" element={<NotFoundPage />} />
            </Route>
            <Route path="*" element={<NotFoundPage />} />
         </Routes>
      </BrowserRouter>
   );
}

export default App;
