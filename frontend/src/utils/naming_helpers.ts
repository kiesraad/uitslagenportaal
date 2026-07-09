import POLLING_STATIONS from '../assets/stembureaus_lisserdam.json'

const FLAT_POLLING_STATIONS = Object.values(POLLING_STATIONS).flat()

export function getPollingStationNumber(stembureau: string) {
  return FLAT_POLLING_STATIONS.find((item) => item.name === stembureau)?.id
}

export function getPollingStationTitle(stembureau: string) {
  const stationNumber = getPollingStationNumber(stembureau)
  const stationName = FLAT_POLLING_STATIONS.find((item) => item.name === stembureau)?.name

  if (!stationNumber) {
    return `Telresultaten stembureau\n${stationName}`
  }

  return `Telresultaten stembureau ${stationNumber}\n${stationName}`
}

export function getPollingStationSubtitle(stembureau: string) {
  const stationName = FLAT_POLLING_STATIONS.find((item) => item.name === stembureau)?.name
  const stationNumber = getPollingStationNumber(stembureau)

  if (!stationNumber) {
    return stationName
  }

  return `Stembureau ${stationNumber} - ${stationName}`
}
