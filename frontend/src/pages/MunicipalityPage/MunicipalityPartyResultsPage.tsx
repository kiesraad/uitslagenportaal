import { useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, useParams } from "react-router";
import { queryClient } from "@/queryClient.ts";
import { ApiError } from "../../api/client.ts";
import { LayoutMain } from "../../components/LayoutMain.tsx";
import PageTop from "../../components/PageTop.tsx";
import PartyCandidatesResultsContent from "../../components/ResultsPage/PartyCandidatesResultsContent.tsx";
import ResultsPageColumns from "../../components/ResultsPage/ResultsPageColumns.tsx";
import { electionConfigQuery, regionQuery } from "../../hooks/queries.ts";
import { useFormatters } from "../../utils/format.ts";
import { getCsbCrumb } from "../../utils/region.ts";
import { appRoutes } from "../../utils/routes.ts";
import { getPartyVoteCount, hasParty } from "../../utils/voteCounts.ts";
import type { Route } from "./+types/MunicipalityPartyResultsPage";

export async function loadMunicipalityPartyResults(
   client: QueryClient,
   { params }: Pick<LoaderFunctionArgs, "params">,
) {
   const [, region] = await Promise.all([
      client.query(electionConfigQuery(params.electionConfigSlug)),
      client.query(regionQuery(params, "gsb")),
   ]);

   // Only an unknown party slug is a 404; empty results mean "not published yet".
   const voteCounts = region.vote_counts;
   if ((voteCounts?.length ?? 0) > 0 && !hasParty(voteCounts, params.partySlug ?? "")) {
      throw new ApiError("Unknown party", 404);
   }
}

export const clientLoader = (args: Route.ClientLoaderArgs) => loadMunicipalityPartyResults(queryClient, args);

export default function MunicipalityPartyResultsPage() {
   const params = useParams();
   // The party is not part of the gemeente request, so its slug is read from the route.
   const partySlug = params.partySlug ?? "";
   const { t } = useLingui();
   const { formatDate } = useFormatters();
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery(params.electionConfigSlug));
   const { data: region } = useSuspenseQuery(regionQuery(params, "gsb"));

   const csbSlug = region.csb?.slug;
   const municipalityResultsRoute = appRoutes.municipalityResults(electionConfig.slug, region.slug, csbSlug);

   const partyName = getPartyVoteCount(region.vote_counts, partySlug)?.party.registered_name ?? t`Lijst`;
   const regionName = region.region_name;
   // No publication date until the region's results have been imported; the line is then omitted.
   const publishedAt = region.results_available_at ? formatDate(region.results_available_at) : null;
   const pageTitle = `${t`Telresultaten gemeente`}\n${regionName}`;
   const documentTitle = t`Telresultaten ${partyName} – gemeente ${regionName}`;

   return (
      <LayoutMain title={documentTitle} description={documentTitle}>
         <PageTop
            title={pageTitle}
            subtitle={publishedAt ? t`Geplaatst op: ${publishedAt}` : undefined}
            breadcrumb={[
               { href: appRoutes.home(), label: t`Home` },
               { href: appRoutes.electionConfigMunicipalityList(electionConfig.slug), label: electionConfig.label },
               getCsbCrumb(region, electionConfig),
               { href: municipalityResultsRoute, label: t`Gemeente ${regionName}` },
               { label: partyName },
            ]}
         />
         <ResultsPageColumns
            previewUrl={region.certified_document_preview_url}
            documentUrl={region.certified_document_url}
         >
            <PartyCandidatesResultsContent
               voteCounts={region.vote_counts}
               partySlug={partySlug}
               issueReportDeadline={electionConfig.issue_report_deadline}
            />
         </ResultsPageColumns>
      </LayoutMain>
   );
}
