// Helper mapping from csb_type to the labels used for that kind of region.
import type { MessageDescriptor } from "@lingui/core";
import { msg } from "@lingui/core/macro";
import type { RegionCategory, RegionSummary } from "../api/types";
import { appRoutes } from "./routes";

/**
 * Labels for one kind of region.
 *
 * `whole` and `withArticle` are whole phrases rather than fragments to be
 * assembled at the call site: Dutch picks `Heel`/`Hele` and `de`/`het` by the
 * noun's gender, which does not survive being composed in application code, so
 * they live in the catalogue where a translator controls them. The mid-sentence
 * form of `singular` comes from `lowercaseFirst`.
 */
export type RegionLabels = {
   /** Standalone, capitalised: "Gemeente". */
   singular: MessageDescriptor;
   /** Standalone, capitalised: "Gemeenten". */
   plural: MessageDescriptor;
   /** The whole region: "Hele gemeente", "Heel waterschap". */
   whole: MessageDescriptor;
   /** With a definite article: "de gemeente", "het waterschap". */
   withArticle: MessageDescriptor;
   /** The CSB name in case it differs from [withArticle] */
   csbName?: MessageDescriptor;
};

const regionTypeMapping: Record<string, RegionLabels> = {
   STAAT: {
      singular: msg`Staat`,
      plural: msg`Staten`,
      whole: msg`Hele staat`,
      withArticle: msg`de staat`,
      csbName: msg`De Kiesraad`,
   },
   WATERSCHAP: {
      singular: msg`Waterschap`,
      plural: msg`Waterschappen`,
      whole: msg`Heel waterschap`,
      withArticle: msg`het waterschap`,
   },
   KIESKRING: {
      singular: msg`Kieskring`,
      plural: msg`Kieskringen`,
      whole: msg`Hele kieskring`,
      withArticle: msg`de kieskring`,
   },
   GEMEENTE: {
      singular: msg`Gemeente`,
      plural: msg`Gemeenten`,
      whole: msg`Hele gemeente`,
      withArticle: msg`de gemeente`,
   },
   PROVINCIE: {
      singular: msg`Provincie`,
      plural: msg`Provincies`,
      whole: msg`Hele provincie`,
      withArticle: msg`de provincie`,
   },
   STEMBUREAU: {
      singular: msg`Stembureau`,
      plural: msg`Stembureaus`,
      whole: msg`Heel stembureau`,
      withArticle: msg`het stembureau`,
   },
};

const FALLBACK_LABELS: RegionLabels = {
   singular: msg`Regio`,
   plural: msg`Regio's`,
   whole: msg`Hele regio`,
   withArticle: msg`de regio`,
};

export function getRegionLabels(regionType?: RegionCategory): RegionLabels {
   if (!regionType) return FALLBACK_LABELS;
   return regionTypeMapping[regionType] ?? FALLBACK_LABELS;
}

export function formatStationLabel(name: string, stationNumber?: number | null): string {
   if (stationNumber == null) {
      return name;
   }
   return `${String(stationNumber).padStart(3, "0")} - ${name}`;
}

export function getCsbCrumb(
   region: { csb?: RegionSummary | null } | undefined,
   electionConfigSlug: string,
): { href: string; label: string } | null {
   const csb = region?.csb;
   if (!csb) return null;
   return { href: appRoutes.csbMunicipalityList(electionConfigSlug, csb.slug), label: csb.region_name };
}
