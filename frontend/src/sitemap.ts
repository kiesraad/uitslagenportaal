import type { LoaderFunctionArgs } from "react-router";
import { getElectionConfigs, getRegions } from "./api/endpoints";
import type { ElectionConfig } from "./api/types";
import { appRoutes } from "./utils/routes";

/** The election and region pages; party and polling-station pages are found through their links. */
async function electionConfigPaths(config: ElectionConfig, withTimeline: boolean): Promise<string[]> {
   const { slug } = config;
   const [csbs, hsbs, municipalities] = await Promise.all([
      getRegions(slug, undefined, config.csb_type),
      config.has_hsb ? getRegions(slug, undefined, "KIESKRING") : [],
      getRegions(slug, undefined, "GEMEENTE"),
   ]);
   return [
      // With a single election the homepage shows the timeline instead.
      ...(withTimeline ? [appRoutes.electionConfigTimeline(slug)] : []),
      appRoutes.electionConfigMunicipalityList(slug),
      ...(config.has_hsb ? [appRoutes.electionConfigHSBList(slug)] : []),
      appRoutes.electionConfigCSBList(slug),
      ...csbs.flatMap((r) => [appRoutes.csbMunicipalityList(slug, r.slug), appRoutes.csbResults(slug, r.slug)]),
      ...hsbs.flatMap((r) => [appRoutes.hsbMunicipalityList(slug, r.slug), appRoutes.hsbResults(slug, r.slug)]),
      ...municipalities.flatMap((r) => [
         appRoutes.municipalityPollingstationList(slug, r.slug, r.csb?.slug),
         appRoutes.municipalityResults(slug, r.slug, r.csb?.slug),
      ]),
   ];
}

export async function loader({ request }: LoaderFunctionArgs) {
   const configs = await getElectionConfigs();
   const configPaths = await Promise.all(configs.map((config) => electionConfigPaths(config, configs.length > 1)));
   const { origin } = new URL(request.url);
   const urls = [appRoutes.home(), ...configPaths.flat()].map((path) => `<url><loc>${origin}${path}</loc></url>`);
   const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.join("\n")}
</urlset>
`;
   return new Response(xml, { headers: { "Content-Type": "application/xml" } });
}
