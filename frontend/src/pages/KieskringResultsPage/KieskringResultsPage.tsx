import { useParams } from "react-router-dom";
// import ResultsNotPublished from "./ResultsNotPublished";
import ResultsAvailable from "./ResultsAvailable";
import '../KieskringResultsPage/search-result-page.css'

export function KieskringResultsPage() {
  const { kieskring: kieskringParam } = useParams<{ kieskring: string }>()
  const kieskring = decodeURIComponent(kieskringParam ?? '')

  return (
    // <ResultsNotPublished kieskring={kieskring} />
    <ResultsAvailable kieskring={kieskring} />
  )
}
