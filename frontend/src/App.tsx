import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { HomePage } from './pages/HomePage'
import { ElectionConfigDetailPage } from './pages/ElectionConfigDetailPage'

import { MunicipalityDetailPage } from './pages/MunicipalityDetailPage/MunicipalityDetailPage'
import PollingStationDetailPage from './pages/PollingStationDetailPage'


function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/:electionConfigSlug/gemeente" element={<ElectionConfigDetailPage />} />
        <Route path="/:electionConfigSlug/:regionSlug" element={<MunicipalityDetailPage />} />
        <Route path="/:electionConfigSlug/:parentRegionSlug/:pollingStationSlug" element={<PollingStationDetailPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
