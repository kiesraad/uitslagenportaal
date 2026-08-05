// Helper mapping from csb_type to singular and plural camelcase versions
import type { RegionCategory } from '../api/types'
import { appRoutes } from './routes'

export type RegionLabels = {
  singular: string
  plural: string
  whole: 'Heel' | 'Hele'
  article: 'de' | 'het'
}

const regionTypeMapping: Record<string, RegionLabels> = {
  STAAT: { singular: "Staat", plural: "Staten", whole: "Hele", article: "de" },
  WATERSCHAP: { singular: "Waterschap", plural: "Waterschappen", whole: "Heel", article: "het" },
  KIESKRING: { singular: "Kieskring", plural: "Kieskringen", whole: "Hele", article: "de" },
  GEMEENTE: { singular: "Gemeente", plural: "Gemeenten", whole: "Hele", article: "de" },
  PROVINCIE: { singular: "Provincie", plural: "Provincies", whole: "Hele", article: "de" },
  STEMBUREAU: { singular: "Stembureau", plural: "Stembureaus", whole: "Heel", article: "het" },
}

const FALLBACK_LABELS: RegionLabels = {
  singular: "Regio",
  plural: "Regio's",
  whole: "Hele",
  article: "de",
}

export function getRegionLabels(regionType?: RegionCategory): RegionLabels {
  if (!regionType) return FALLBACK_LABELS
  return regionTypeMapping[regionType] ?? FALLBACK_LABELS
}

export function getCsbCrumb(
  region: { csb_name?: string | null; csb_slug?: string | null } | undefined,
  electionConfigSlug: string,
): { href: string; label: string } | null {
  if (!region?.csb_name || !region.csb_slug) return null
  return { href: appRoutes.csbMunicipalityList(electionConfigSlug, region.csb_slug), label: region.csb_name }
}
