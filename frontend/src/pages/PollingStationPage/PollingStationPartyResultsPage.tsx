import { useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, useParams } from "react-router";
import { ApiError } from "../../api/client.ts";
import { LayoutMain } from "../../components/LayoutMain.tsx";
import PageTop from "../../components/PageTop";
import PartyCandidatesResultsContent from "../../components/ResultsPage/PartyCandidatesResultsContent";
import ResultsPageColumns from "../../components/ResultsPage/ResultsPageColumns";
import { useFormatters } from "../../utils/format";
import { formatStationLabel, getCsbCrumb } from "../../utils/region";
import { appRoutes } from "../../utils/routes";
import { getPartyVoteCount, hasParty } from "../../utils/voteCounts";
import { pollingStationQueries } from "./PollingStationResultsPage.tsx";

export async function loadPollingStationPartyResults(
   client: QueryClient,
   { params }: Pick<LoaderFunctionArgs, "params">,
) {
   const queries = pollingStationQueries(params);
   const [, , pollingStation] = await Promise.all([
      client.query(queries.electionConfig),
      client.query(queries.region),
      client.query(queries.pollingStation),
   ]);

   // Only an unknown party slug is a 404; empty results mean "not published yet".
   const voteCounts = pollingStation.vote_counts;
   if ((voteCounts?.length ?? 0) > 0 && !hasParty(voteCounts, params.partySlug ?? "")) {
      throw new ApiError("Unknown party", 404);
   }
}

export default function PollingStationPartyResultsPage() {
   const params = useParams();
   const queries = pollingStationQueries(params);
   // The party is not part of the stembureau request, so its slug is read from the route.
   const partySlug = params.partySlug ?? "";
   const { t } = useLingui();
   const { formatDate } = useFormatters();
   const { data: electionConfig } = useSuspenseQuery(queries.electionConfig);
   const { data: region } = useSuspenseQuery(queries.region);
   const { data: pollingStation } = useSuspenseQuery(queries.pollingStation);

   const csbSlug = region.csb?.slug;
   const municipalityPollingstationListRoute = appRoutes.municipalityPollingstationList(
      electionConfig.slug,
      region.slug,
      csbSlug,
   );
   const pollingStationResultsRoute = appRoutes.pollingStationResults(
      electionConfig.slug,
      region.slug,
      pollingStation.slug,
      csbSlug,
   );

   const partyName = getPartyVoteCount(pollingStation.vote_counts, partySlug)?.party.registered_name ?? t`Lijst`;
   const stationName = pollingStation.region_name;
   const stationLabel = formatStationLabel(stationName, pollingStation.station_number);
   // No publication date until the region's results have been imported; the line is then omitted.
   const publishedAt = region.results_available_at ? formatDate(region.results_available_at) : null;
   const pageTitle = `${t`Telresultaten stembureau`}\n${stationName}`;
   const documentTitle = t`Telresultaten ${partyName} – stembureau ${stationName}`;

   return (
      <LayoutMain title={documentTitle} description={documentTitle}>
         <PageTop
            title={pageTitle}
            subtitle={publishedAt ? t`Geplaatst op: ${publishedAt}` : undefined}
            breadcrumb={[
               { href: appRoutes.home(), label: t`Home` },
               { href: appRoutes.electionConfigMunicipalityList(electionConfig.slug), label: electionConfig.label },
               getCsbCrumb(region, electionConfig),
               { href: municipalityPollingstationListRoute, label: t`Gemeente ${region.region_name}` },
               { href: pollingStationResultsRoute, label: stationLabel },
            ]}
         />
         <ResultsPageColumns
            previewUrl={pollingStation.certified_document_preview_url}
            documentUrl={pollingStation.certified_document_url}
         >
            <PartyCandidatesResultsContent
               voteCounts={pollingStation.vote_counts}
               partySlug={partySlug}
               issueReportDeadline={electionConfig.issue_report_deadline}
            />
         </ResultsPageColumns>
      </LayoutMain>
   );
}
