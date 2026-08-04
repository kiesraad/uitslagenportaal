import {Link, useNavigate} from 'react-router-dom'
import type {SearchListOption} from '../SearchBar'
import SearchBar from '../SearchBar'
import type {ElectionConfig, Region, RegionCategory} from '../../api/types'
import {appRoutes} from '../../utils/routes'
import {getRegionLabel} from '../../utils/region'
import {type PropsWithChildren, useMemo} from "react";
import {twMerge} from "tailwind-merge";


function compareByStationNumber(a: SearchListOption, b: SearchListOption): number {
  return (a.stationNumber ?? 0) - (b.stationNumber ?? 0)
}

type Props = {
  electionConfig: ElectionConfig
  regions: Region[] | undefined
  regionCategory: Extract<RegionCategory, 'GEMEENTE' | 'STEMBUREAU' | 'WATERSCHAP'>
  parentRegionSlug?: string
  parentCsbSlug?: string
  regionTitle?: string
}

export function RegionList({
  electionConfig,
  regions,
  regionCategory,
  parentRegionSlug,
  parentCsbSlug,
  regionTitle
}: Props) {


  const navigate = useNavigate()

  function navigateToGemeente(option: SearchListOption) {
    navigate(appRoutes.municipalityPollingstationList(electionConfig.slug ?? '', option.id, option.csbSlug))
  }

  function navigateToPollingStation(option: SearchListOption) {
    if (!parentRegionSlug) return
    navigate(appRoutes.pollingStationResults(electionConfig.slug, parentRegionSlug, option.id, parentCsbSlug))
  }

  function navigateToWaterschap(option: SearchListOption) {
    navigate(appRoutes.csbResults(electionConfig.slug ?? '', option.id))
  }

  let navigateToRegion: (option: SearchListOption) => void;
  if (regionCategory === 'STEMBUREAU') {
    navigateToRegion = navigateToPollingStation;
  } else if (regionCategory === 'WATERSCHAP') {
    navigateToRegion = navigateToWaterschap;
  } else {
    navigateToRegion = navigateToGemeente;
  }

  function getRegionRoute(option: SearchListOption) {
    if (regionCategory === 'STEMBUREAU' && parentRegionSlug) {
      return appRoutes.pollingStationResults(electionConfig.slug, parentRegionSlug, option.id, parentCsbSlug)
    } else if (regionCategory === 'WATERSCHAP') {
      return appRoutes.csbResults(electionConfig.slug, option.id)
    } else {
      return appRoutes.municipalityPollingstationList(electionConfig.slug, option.id, option.csbSlug)
    }
  }

  const isPollingStationList = regionCategory === 'STEMBUREAU'

  const regionOptions: SearchListOption[] = useMemo(() => {
    const visibleRegions = (regions ?? []).filter((region) => region.region_name)

    const nameCounts = visibleRegions.reduce<Record<string, number>>((counts, region) => {
      counts[region.region_name] = (counts[region.region_name] ?? 0) + 1
      return counts
    }, {})

    return visibleRegions.map((region) => {
      const isAmbiguous = nameCounts[region.region_name] > 1 && Boolean(region.csb_name)
      const label = isAmbiguous ? `${region.region_name} - ${region.csb_name}` : region.region_name
      return {
        id: region.slug,
        label,
        sortName: region.region_name,
        stationNumber: isPollingStationList ? region.station_number ?? undefined : undefined,
        csbSlug: region.csb_slug ?? undefined,
      }
    })
  }, [regions, isPollingStationList])

  const sortedPollingStations = useMemo(
    () => regionOptions.slice().sort(compareByStationNumber),
    [regionOptions]
  )

  const regionsByLetter = useMemo(() => {
    const grouped = regionOptions.reduce<Record<string, SearchListOption[]>>((grouped, option) => {
      const sortName = option.sortName ?? option.label
      // handle 's-Gravenhage and 's-Hertogenbosch
      const name = sortName.startsWith("'s-") ? sortName.slice(3) : sortName
      const letter = name[0].toUpperCase()
      ;(grouped[letter] ??= []).push(option)
      return grouped
    }, {})

    return Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b))
  }, [regionOptions])

  return (
    <div className="page-main">

      {isPollingStationList && (<h2 className="mb-4 text-2xl font-bold font-title">
        {sortedPollingStations.length} stembureaus in {regionTitle}
      </h2>)}

      <SearchBar
        regionCategory={regionCategory}
        options={regionOptions}
        onSelect={navigateToRegion}
      />

      {!isPollingStationList && (<h2 className="mb-4 text-2xl font-bold font-title">
        Vind een {getRegionLabel(regionCategory).toLowerCase()} van A tot Z
      </h2>)}

      {isPollingStationList ? (
        <SearchList>
          {sortedPollingStations.map((station) => (
            <ListOptionLink
              key={`${station.id}-${station.csbSlug ?? ''}`}
              listOption={station}
              to={getRegionRoute(station)}
            />
          ))}
        </SearchList>
      ) : (
        regionsByLetter.map(([letter, municipalities]) => (
          <div key={letter} className="mb-6">
            <div className="font-bold my-2 text-xl">{letter}</div>
            <SearchList>
              {municipalities.map((municipality) => (
                <ListOptionLink
                  key={`${municipality.id}-${municipality.csbSlug ?? ''}`}
                  listOption={municipality}
                  to={getRegionRoute(municipality)}
                />
              ))}
            </SearchList>
          </div>
        ))
      )}
    </div>
  )
}

function SearchList({children}: PropsWithChildren) {
  return (
    <div className="mb-5 max-w-2xl grid grid-cols-[max-content_auto_max-content]">
      {children}
    </div>
  )
}

function ListOptionLink({listOption, to}: {
  listOption: SearchListOption,
  to: string
}) {
  return (
    <Link
      to={to}
      className="items-center hover:no-underline! odd:bg-blue-50 hover:bg-blue-100 py-4 px-6 grid col-span-3 grid-cols-subgrid"
    >
      <span className={twMerge(listOption.stationNumber && "font-light text-gray-700 pr-2")}>{listOption.stationNumber}</span>
      <span className="underline">{listOption.label}</span>
      <span className="gemeente-chevron">{'>'}</span>
    </Link>
  )
}
