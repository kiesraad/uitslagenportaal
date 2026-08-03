import {PageQueryBoundary} from '../../components/PageQueryBoundary.tsx'
import {useRegions} from '../../hooks/queries.ts'
import {RegionList} from '../../components/ListPage/RegionList.tsx'
import {Navigate, useOutletContext} from "react-router";
import type {ElectionConfig, Region} from "@/api/types.ts";
import HtmlHead from "@/components/HtmlHead.tsx";
import {appRoutes} from "@/utils/routes.ts";


export function MunicipalityPollingstationListPage() {
  const {electionConfig, region, municipalityTitle, electionConfigSlug, regionSlug, csbSlug} = useOutletContext<{
    electionConfig: ElectionConfig,
    region: Region,
    municipalityTitle: string,
    electionConfigSlug: string,
    regionSlug: string,
    csbSlug: string,
  }>();
  const municipalityResultsRoute = appRoutes.municipalityResults(electionConfigSlug ?? '', regionSlug, csbSlug)

  const {
    data: pollingStations,
    isLoading: isPollingStationsLoading,
    isError: isPollingStationsError,
    refetch: refetchPollingStations,
  } = useRegions(electionConfigSlug, regionSlug, 'STEMBUREAU', false, csbSlug)

  const isLoading = isPollingStationsLoading
  const isError =
    isPollingStationsError ||
    !electionConfig ||
    !pollingStations

  if (isLoading || isError) {
    return (
      <PageQueryBoundary
        isLoading={isLoading}
        isError={isError}
        onRetry={() => {
          void refetchPollingStations()
        }}
        entityLabel="Gemeente"
      />
    )
  }

  const hasResults = Array.isArray(region.vote_counts) && region.vote_counts.length > 0
  if (!hasResults) {
    return <Navigate to={municipalityResultsRoute} replace/>
  }

  const municipalityTitle = `Gemeente ${region.region_name}`

  return (
    <>
      <HtmlHead title={`Resultaten ${municipalityTitle} per stembureau`}/>
      <RegionList
        electionConfig={electionConfig}
        regions={pollingStations}
        parentRegionSlug={regionSlug}
        parentCsbSlug={csbSlug}
        regionTitle={municipalityTitle}
        regionCategory='STEMBUREAU'
      />
    </>


  )
}
