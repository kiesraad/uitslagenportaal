// Helper mapping from csb_type to the labels used for that kind of region.
import type { MessageDescriptor } from "@lingui/core";
import { msg } from "@lingui/core/macro";
import type { RegionCategory } from "../api/types";
import { appRoutes } from "./routes";

/**
 * Labels for one kind of region.
 *
 * Each field is a whole phrase rather than a fragment to be assembled at the
 * call site. Dutch picks `Heel`/`Hele` and `de`/`het` by the noun's gender, and
 * lowercasing a noun mid-sentence is wrong in languages that always capitalise
 * them — neither survives being composed in application code, so both live in
 * the catalogue where a translator controls them.
 */
export type RegionLabels = {
   /** Standalone, capitalised: "Gemeente". */
   singular: MessageDescriptor;
   /** Standalone, capitalised: "Gemeenten". */
   plural: MessageDescriptor;
   /** Mid-sentence: "gemeente". */
   inline: MessageDescriptor;
   /** The whole region: "Hele gemeente", "Heel waterschap". */
   whole: MessageDescriptor;
   /** With a definite article: "de gemeente", "het waterschap". */
   withArticle: MessageDescriptor;
};

// Wrapped so a bundler may drop it when unused; module-scope `msg` calls are
// otherwise side effects it has to keep.
const regionTypeMapping: Record<string, RegionLabels> = /* @__PURE__ */ (() => ({
   STAAT: {
      singular: msg`Staat`,
      plural: msg`Staten`,
      inline: msg`staat`,
      whole: msg`Hele staat`,
      withArticle: msg`de staat`,
   },
   WATERSCHAP: {
      singular: msg`Waterschap`,
      plural: msg`Waterschappen`,
      inline: msg`waterschap`,
      whole: msg`Heel waterschap`,
      withArticle: msg`het waterschap`,
   },
   KIESKRING: {
      singular: msg`Kieskring`,
      plural: msg`Kieskringen`,
      inline: msg`kieskring`,
      whole: msg`Hele kieskring`,
      withArticle: msg`de kieskring`,
   },
   GEMEENTE: {
      singular: msg`Gemeente`,
      plural: msg`Gemeenten`,
      inline: msg`gemeente`,
      whole: msg`Hele gemeente`,
      withArticle: msg`de gemeente`,
   },
   PROVINCIE: {
      singular: msg`Provincie`,
      plural: msg`Provincies`,
      inline: msg`provincie`,
      whole: msg`Hele provincie`,
      withArticle: msg`de provincie`,
   },
   STEMBUREAU: {
      singular: msg`Stembureau`,
      plural: msg`Stembureaus`,
      inline: msg`stembureau`,
      whole: msg`Heel stembureau`,
      withArticle: msg`het stembureau`,
   },
}))();

const FALLBACK_LABELS: RegionLabels = (() => ({
   singular: msg`Regio`,
   plural: msg`Regio's`,
   inline: msg`regio`,
   whole: msg`Hele regio`,
   withArticle: msg`de regio`,
}))();

export function getRegionLabels(regionType?: RegionCategory): RegionLabels {
   if (!regionType) return FALLBACK_LABELS;
   return regionTypeMapping[regionType] ?? FALLBACK_LABELS;
}

export function getCsbCrumb(
   region: { csb_name?: string | null; csb_slug?: string | null } | undefined,
   electionConfigSlug: string,
): { href: string; label: string } | null {
   if (!region?.csb_name || !region.csb_slug) return null;
   return { href: appRoutes.csbMunicipalityList(electionConfigSlug, region.csb_slug), label: region.csb_name };
}
