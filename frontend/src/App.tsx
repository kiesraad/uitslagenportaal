import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { HomePage } from './pages/HomePage'
import { GemeentePage } from './pages/GemeentePage'
import { KieskringPage } from './pages/KieskringPage'
import { NederlandPage } from './pages/NederlandPage'
import { GemeenteSearchResultPage } from './pages/GemeenteSearchResultPage/GemeenteSearchResultPage'
import HeleGemeenteResults from './pages/GemeenteSearchResultPage/HeleGemeenteResults'
import StembureauResults from './pages/GemeenteSearchResultPage/StembureauResults'
import PartyLevel from './pages/GemeenteSearchResultPage/PartyLevel'
import ReportError from './pages/GemeenteSearchResultPage/ReportError'
import { KieskringResultsPage } from './pages/KieskringResultsPage/KieskringResultsPage'
import KieskringPerGemeente from './pages/KieskringResultsPage/PerGemeente'
import ResultsForCandidate from './pages/NederlandResultsPage/ResultsForCandidate'
import ResultsList3Table from './pages/NederlandResultsPage/ResultsList3Table'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/gemeente" element={<GemeentePage />} />
        <Route path="/gemeente/:gemeente" element={<GemeenteSearchResultPage />} />
        <Route path="/gemeente/resultaten/:gemeente" element={<HeleGemeenteResults />} />
        <Route path="/gemeente/resultaten/:gemeente/partij/:party" element={<PartyLevel />} />
        <Route path="/gemeente/:gemeente/stembureau/resultaten/:stembureau" element={<StembureauResults />} />
        <Route path="/gemeente/:gemeente/stembureau/resultaten/:stembureau/partij/:party" element={<PartyLevel />} />
        <Route path="/stembureau/resultaten/:stembureau" element={<StembureauResults />} />

        <Route path="/kieskring" element={<KieskringPage />} />
        <Route path="/kieskring/:kieskring" element={<KieskringResultsPage />} />
        <Route path="/kieskring/:kieskring/gemeente" element={<KieskringPerGemeente />} />

        <Route path="/nederland" element={<NederlandPage />} />
        <Route path="/nederland/lijst/:listNumber/:list" element={<ResultsList3Table />} />
        <Route path="/nederland/lijst/:listNumber/:list/kandidaat/:candidate" element={<ResultsForCandidate />} />

        <Route path="/gemeente/:gemeente/fout-melden" element={<ReportError />} />
        <Route path="/gemeente/:gemeente/stembureau/resultaten/:stembureau/fout-melden" element={<ReportError />} />
        <Route path="/fout-melden" element={<ReportError />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
