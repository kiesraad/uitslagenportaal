// Helper mapping from csb_type to the labels used for that kind of region.
import type { MessageDescriptor } from "@lingui/core";
import { msg } from "@lingui/core/macro";
import type { RegionCategory, RegionSummary } from "../api/types";
import { appRoutes } from "./routes";

/**
 * Labels for one kind of region.
 *
 * `whole`, `withArticle` and `name` are whole phrases rather than fragments
 * to be assembled at the call site: Dutch picks `Heel`/`Hele` and `de`/`het` by
 * the noun's gender, and English says "the municipality of Utrecht", neither of
 * which survives being composed in application code, so they live in the
 * catalogue where a translator controls them. The mid-sentence form of
 * `singular` comes from `lowercaseFirst`.
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
   /** The name as used in texts, e.g. "gemeente Utrecht" or "Nederland". Resolve with `regionWithName`. */
   name: MessageDescriptor;
   /** The CSB name, when it is not the region's `withArticle`. */
   csbName?: MessageDescriptor;
};

const regionTypeMapping: Record<string, RegionLabels> = {
   STAAT: {
      singular: msg`Staat`,
      plural: msg`Staten`,
      whole: msg`Hele staat`,
      withArticle: msg`de staat`,
      name: msg({ message: "Nederland" }),
      csbName: msg`De Kiesraad`,
   },
   WATERSCHAP: {
      singular: msg`Waterschap`,
      plural: msg`Waterschappen`,
      whole: msg`Heel waterschap`,
      withArticle: msg`het waterschap`,
      name: msg({ message: "waterschap {name}" }),
   },
   KIESKRING: {
      singular: msg`Kieskring`,
      plural: msg`Kieskringen`,
      whole: msg`Hele kieskring`,
      withArticle: msg`de kieskring`,
      name: msg({ message: "kieskring {name}" }),
   },
   GEMEENTE: {
      singular: msg`Gemeente`,
      plural: msg`Gemeenten`,
      whole: msg`Hele gemeente`,
      withArticle: msg`de gemeente`,
      name: msg({ message: "gemeente {name}" }),
   },
   PROVINCIE: {
      singular: msg`Provincie`,
      plural: msg`Provincies`,
      whole: msg`Hele provincie`,
      withArticle: msg`de provincie`,
      name: msg({ message: "provincie {name}" }),
   },
   STEMBUREAU: {
      singular: msg`Stembureau`,
      plural: msg`Stembureaus`,
      whole: msg`Heel stembureau`,
      withArticle: msg`het stembureau`,
      name: msg({ message: "stembureau {name}" }),
   },
};

const FALLBACK_LABELS: RegionLabels = {
   singular: msg`Regio`,
   plural: msg`Regio's`,
   whole: msg`Hele regio`,
   withArticle: msg`de regio`,
   name: msg({ message: "regio {name}" }),
};

export function getRegionLabels(regionType?: RegionCategory): RegionLabels {
   if (!regionType) return FALLBACK_LABELS;
   return regionTypeMapping[regionType] ?? FALLBACK_LABELS;
}

/** The `name` phrase for a region, ready for `t()`: "gemeente Utrecht". */
export function regionWithName(regionType: RegionCategory | undefined, name: string): MessageDescriptor {
   return { ...getRegionLabels(regionType).name, values: { name } };
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
