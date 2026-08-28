import { useLingui } from "@lingui/react/macro";
import { useSuspenseQuery } from "@tanstack/react-query";
import { useLoaderData, useParams } from "react-router";
import type { MunicipalityLoaderData } from "@/pages/MunicipalityPage/MunicipalityResultsPage.tsx";
import { LayoutMain } from "../../components/LayoutMain.tsx";
import PageTop from "../../components/PageTop.tsx";
import PartyCandidatesResultsContent from "../../components/ResultsPage/PartyCandidatesResultsContent.tsx";
import { useFormatters } from "../../utils/format.ts";
import { getCsbCrumb } from "../../utils/region.ts";
import { appRoutes } from "../../utils/routes.ts";
import { getPartyVoteCount, hasParty } from "../../utils/voteCounts.ts";
import { NotFoundPage } from "../NotFoundPage.tsx";

export function MunicipalityPartyResultsPage() {
   const { electionConfigQuery, regionQuery } = useLoaderData<MunicipalityLoaderData>();
   // The party is not part of the gemeente request, so its slug is read from the route.
   const { partySlug = "" } = useParams<{ partySlug: string }>();
   const { t } = useLingui();
   const { formatDate } = useFormatters();
   // The loader has already resolved both queries, so the data is never pending here.
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery);
   const { data: region } = useSuspenseQuery(regionQuery);

   const csbSlug = region.csb_slug ?? undefined;
   const municipalityResultsRoute = appRoutes.municipalityResults(electionConfig.slug, region.slug, csbSlug);
   const municipalityPartyResultsRoute = appRoutes.municipalityPartyResults(
      electionConfig.slug,
      region.slug,
      partySlug,
      csbSlug,
   );

   // Only an unknown party slug is a 404; empty results mean "not published yet"
   const hasAnyResults = (region.vote_counts?.length ?? 0) > 0;
   if (hasAnyResults && !hasParty(region.vote_counts, partySlug)) {
      return <NotFoundPage />;
   }

   const partyName = getPartyVoteCount(region.vote_counts, partySlug)?.party.registered_name ?? t`Lijst`;
   const regionName = region.region_name;
   // No publication date until the region's results have been imported; the line is then omitted.
   const publishedAt = region.results_available_at ? formatDate(region.results_available_at) : null;
   const pageTitle = `${t`Telresultaten gemeente`}\n${regionName}`;
   const documentTitle = t`Telresultaten gemeente – ${regionName}`;

   return (
      <LayoutMain title={documentTitle} description={documentTitle}>
         <PageTop
            title={pageTitle}
            subtitle={publishedAt ? t`Geplaatst op: ${publishedAt}` : undefined}
            breadcrumb={[
               { href: appRoutes.home(), label: t`Home` },
               { href: appRoutes.electionConfigMunicipalityList(electionConfig.slug), label: electionConfig.label },
               getCsbCrumb(region, electionConfig.slug),
               { href: municipalityResultsRoute, label: t`Gemeente ${regionName}` },
               { href: municipalityPartyResultsRoute, label: partyName },
            ]}
         />
         <div className="page-main page-main-two-columns">
            <div className="page-space-3">
               <PartyCandidatesResultsContent
                  voteCounts={region.vote_counts}
                  partySlug={partySlug}
                  issueReportDeadline={electionConfig.issue_report_deadline}
               />
            </div>
         </div>
      </LayoutMain>
   );
}
