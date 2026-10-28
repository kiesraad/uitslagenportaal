// Helper mapping from csb_type to the labels used for that kind of region.
import type { MessageDescriptor } from "@lingui/core";
import { msg } from "@lingui/core/macro";
import type { ElectionConfig, RegionCategory, RegionSummary } from "../api/types";
import { appRoutes } from "./routes";

/**
 * Labels for one kind of region.
 *
 * `whole`, `withArticle` and `withName` are whole phrases rather than fragments
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
   /** With a definite article and a `{name}`: "de gemeente Utrecht". Resolve with `regionWithName`. */
   withName: MessageDescriptor;
   /** The CSB name in case it differs from [withArticle] */
   csbName?: MessageDescriptor;
};

const regionTypeMapping: Record<string, RegionLabels> = {
   STAAT: {
      singular: msg`Staat`,
      plural: msg`Staten`,
      whole: msg`Hele staat`,
      withArticle: msg`de staat`,
      withName: msg({ message: "de staat {name}" }),
      csbName: msg`De Kiesraad`,
   },
   WATERSCHAP: {
      singular: msg`Waterschap`,
      plural: msg`Waterschappen`,
      whole: msg`Heel waterschap`,
      withArticle: msg`het waterschap`,
      withName: msg({ message: "het waterschap {name}" }),
   },
   KIESKRING: {
      singular: msg`Kieskring`,
      plural: msg`Kieskringen`,
      whole: msg`Hele kieskring`,
      withArticle: msg`de kieskring`,
      withName: msg({ message: "de kieskring {name}" }),
   },
   GEMEENTE: {
      singular: msg`Gemeente`,
      plural: msg`Gemeenten`,
      whole: msg`Hele gemeente`,
      withArticle: msg`de gemeente`,
      withName: msg({ message: "de gemeente {name}" }),
   },
   PROVINCIE: {
      singular: msg`Provincie`,
      plural: msg`Provincies`,
      whole: msg`Hele provincie`,
      withArticle: msg`de provincie`,
      withName: msg({ message: "de provincie {name}" }),
   },
   STEMBUREAU: {
      singular: msg`Stembureau`,
      plural: msg`Stembureaus`,
      whole: msg`Heel stembureau`,
      withArticle: msg`het stembureau`,
      withName: msg({ message: "het stembureau {name}" }),
   },
};

const FALLBACK_LABELS: RegionLabels = {
   singular: msg`Regio`,
   plural: msg`Regio's`,
   whole: msg`Hele regio`,
   withArticle: msg`de regio`,
   withName: msg({ message: "de regio {name}" }),
};

export function getRegionLabels(regionType?: RegionCategory): RegionLabels {
   if (!regionType) return FALLBACK_LABELS;
   return regionTypeMapping[regionType] ?? FALLBACK_LABELS;
}

/** The `withName` phrase for a region, ready for `t()`: "de gemeente Utrecht". */
export function regionWithName(regionType: RegionCategory | undefined, name: string): MessageDescriptor {
   return { ...getRegionLabels(regionType).withName, values: { name } };
}

/** TK and EP always have HSBs, but `has_hsb` only reports them once regions are imported. */
export function electionHasHsb(electionConfig: Pick<ElectionConfig, "csb_type" | "has_hsb" | "single_csb">): boolean {
   return electionConfig.has_hsb || (electionConfig.csb_type === "STAAT" && !electionConfig.single_csb);
}

export function formatStationLabel(name: string, stationNumber?: number | null): string {
   if (stationNumber == null) {
      return name;
   }
   return `${String(stationNumber).padStart(3, "0")} - ${name}`;
}

export function getCsbCrumb(
   region: { csb?: RegionSummary | null } | undefined,
   electionConfig: Pick<ElectionConfig, "slug" | "single_csb">,
): { href: string; label: string } | null {
   const csb = region?.csb;
   if (!csb) return null;
   // A single CSB has no list to pick it from: link to its results, as the CSB tab does.
   const href = electionConfig.single_csb
      ? appRoutes.electionConfigCSBList(electionConfig.slug)
      : appRoutes.csbMunicipalityList(electionConfig.slug, csb.slug);
   return { href, label: csb.region_name };
}
