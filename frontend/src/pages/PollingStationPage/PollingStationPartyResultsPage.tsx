import { useLingui } from "@lingui/react/macro";
import { useSuspenseQuery } from "@tanstack/react-query";
import { useLoaderData, useParams } from "react-router";
import { LayoutMain } from "../../components/LayoutMain.tsx";
import PageTop from "../../components/PageTop";
import PartyCandidatesResultsContent from "../../components/ResultsPage/PartyCandidatesResultsContent";
import { useFormatters } from "../../utils/format";
import { getCsbCrumb } from "../../utils/region";
import { appRoutes } from "../../utils/routes";
import { getPartyVoteCount, hasParty } from "../../utils/voteCounts";
import { NotFoundPage } from "../NotFoundPage";
import type { PollingStationLoaderData } from "./PollingStationResultsPage.tsx";

export default function PollingStationPartyResultsPage() {
   const { electionConfigQuery, regionQuery, pollingStationQuery } = useLoaderData<PollingStationLoaderData>();
   // The party is not part of the stembureau request, so its slug is read from the route.
   const { partySlug = "" } = useParams<{ partySlug: string }>();
   const { t } = useLingui();
   const { formatDate } = useFormatters();
   // The loader has already resolved every query, so the data is never pending here.
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery);
   const { data: region } = useSuspenseQuery(regionQuery);
   const { data: pollingStation } = useSuspenseQuery(pollingStationQuery);

   const csbSlug = region.csb_slug ?? undefined;
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
   const pollingStationPartyResultsRoute = appRoutes.pollingStationPartyResults(
      electionConfig.slug,
      region.slug,
      pollingStation.slug,
      partySlug,
      csbSlug,
   );

   const partyName = getPartyVoteCount(pollingStation.vote_counts, partySlug)?.party.registered_name ?? t`Lijst`;
   const stationName = pollingStation.region_name;
   // No publication date until the region's results have been imported; the line is then omitted.
   const publishedAt = region.results_available_at ? formatDate(region.results_available_at) : null;
   const pageTitle = `${t`Telresultaten stembureau`}\n${stationName}`;
   const documentTitle = t`Telresultaten stembureau – ${stationName}`;

   // Only an unknown party slug is a 404; empty results mean "not published yet"
   const hasAnyResults = (pollingStation.vote_counts?.length ?? 0) > 0;
   if (hasAnyResults && !hasParty(pollingStation.vote_counts, partySlug)) {
      return <NotFoundPage />;
   }

   return (
      <LayoutMain title={documentTitle} description={documentTitle}>
         <PageTop
            title={pageTitle}
            subtitle={publishedAt ? t`Geplaatst op: ${publishedAt}` : undefined}
            breadcrumb={[
               { href: appRoutes.home(), label: t`Home` },
               { href: appRoutes.electionConfigMunicipalityList(electionConfig.slug), label: electionConfig.label },
               getCsbCrumb(region, electionConfig.slug),
               { href: municipalityPollingstationListRoute, label: region.region_name },
               { href: pollingStationResultsRoute, label: pollingStation.region_name },
               { href: pollingStationPartyResultsRoute, label: partyName },
            ]}
         />
         <div className="page-main page-main-two-columns">
            <div className="page-space-3">
               <PartyCandidatesResultsContent
                  voteCounts={pollingStation.vote_counts}
                  partySlug={partySlug}
                  issueReportDeadline={electionConfig.issue_report_deadline}
               />
            </div>
         </div>
      </LayoutMain>
   );
}
