import { useParams } from "react-router-dom";
// import ResultsNotPublished from "./ResultsNotPublished";
import ResultsAvailable from "./ResultsAvailable";
import './search-result-page.css'

export function GemeenteSearchResultPage() {
  const { gemeente: gemeenteParam } = useParams<{ gemeente: string }>()
  const gemeente = decodeURIComponent(gemeenteParam ?? '')

  return (
    // <ResultsNotPublished gemeente={gemeente} />
    <ResultsAvailable gemeente={gemeente} />
  )
}
