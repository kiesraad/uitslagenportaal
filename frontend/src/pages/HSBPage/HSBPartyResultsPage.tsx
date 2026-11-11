import { Trans, useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, useParams } from "react-router";
import { HSBTimeline } from "@/components/Timeline/HSBTimeline.tsx";
import { queryClient } from "@/queryClient.ts";
import { ApiError } from "../../api/client.ts";
import { LayoutMain } from "../../components/LayoutMain.tsx";
import PageTop from "../../components/PageTop.tsx";
import IssueNotice from "../../components/ResultsPage/IssueNotice.tsx";
import PartyVoteMatrixTable from "../../components/ResultsPage/PartyVoteMatrixTable.tsx";
import ResultsNotPublished from "../../components/ResultsPage/ResultsNotPublished.tsx";
import ResultsPageIndex from "../../components/ResultsPage/ResultsPageIndex";
import { electionConfigQuery, hsbPartyVoteMatrixQuery, regionQuery } from "../../hooks/queries.ts";
import { useFormatters } from "../../utils/format.ts";
import { getCsbCrumb, getRegionLabels } from "../../utils/region.ts";
import { appRoutes } from "../../utils/routes.ts";
import { getPartyVoteCount } from "../../utils/voteCounts.ts";
import type { Route } from "./+types/HSBPartyResultsPage";

export async function loadHSBPartyResults(client: QueryClient, { params }: Pick<LoaderFunctionArgs, "params">) {
   const [electionConfig, region] = await Promise.all([
      client.query(electionConfigQuery(params.electionConfigSlug)),
      client.query(regionQuery(params, "hsb")),
   ]);

   if (!electionConfig.has_hsb) {
      throw new ApiError("Election has no HSBs", 404);
   }

   // Only the region response names the election the matrix is asked for.
   await client.query(hsbPartyVoteMatrixQuery(region.election_slug, params.regionSlug, params.partySlug));
}

export const clientLoader = (args: Route.ClientLoaderArgs) => loadHSBPartyResults(queryClient, args);

export default function HSBPartyResultsPage() {
   const params = useParams();
   const { t } = useLingui();
   const { formatDate } = useFormatters();
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery(params.electionConfigSlug));
   const { data: region } = useSuspenseQuery(regionQuery(params, "hsb"));
   const { data: partyVoteMatrix } = useSuspenseQuery(
      hsbPartyVoteMatrixQuery(region.election_slug, params.regionSlug, params.partySlug),
   );

   const regionLabels = getRegionLabels("KIESKRING");
   const partySlug = partyVoteMatrix.party.slug;
   const partyName = partyVoteMatrix.party.registered_name;
   const hasResults = partyVoteMatrix.rows.length > 0;

   const listNumber = getPartyVoteCount(region.vote_counts, partySlug)?.party.list_number ?? "-";
   const regionType = t(regionLabels.singular);
   const regionName = region.region_name;
   const publishedAt = region.results_available_at ? formatDate(region.results_available_at) : null;

   const resultsPageContent = (
      <>
         <ResultsPageIndex />
         <section id="telresultaten" className="party-vote-matrix-section">
            <h2 className="mb-4.5 text-lg font-medium">
               <Trans>Telresultaten lijst {listNumber}</Trans>
            </h2>
            <h3 className="party-level-title mb-2">{partyName}</h3>

            <p className="mb-4 max-w-160">
               <Trans>
                  Het hoofdstembureau heeft de telresultaten van alle gemeenten in de kieskring gecontroleerd,
                  overgenomen en bij elkaar opgeteld. Hieronder ziet u de telresultaten zoals ze zijn opgenomen in het
                  proces-verbaal van het hoofdstembureau.
               </Trans>
            </p>
            <PartyVoteMatrixTable
               matrix={partyVoteMatrix}
               caption={<Trans>Stemmen per kandidaat per gemeente</Trans>}
            />
         </section>
      </>
   );

   return (
      <LayoutMain title={t`Telresultaten ${partyName} – ${regionType} ${regionName}`}>
         <PageTop
            title={`${t`Telresultaten ${regionType} ${regionName}`}\n ${partyName}`}
            subtitle={publishedAt ? t`Geplaatst op: ${publishedAt}` : undefined}
            breadcrumb={[
               { href: appRoutes.home(), label: t`Home` },
               {
                  href: appRoutes.electionConfigMunicipalityList(electionConfig.slug),
                  label: electionConfig.label,
               },
               getCsbCrumb(region, electionConfig),
               { href: appRoutes.hsbResults(electionConfig.slug, region.slug), label: region.region_name },
               { label: partyName },
            ]}
         />
         <div className="page-main">
            <div className="party-vote-matrix-page flex flex-col gap-4 sm:gap-12">
               {!hasResults ? (
                  <ResultsNotPublished regionName={region.region_name} regionCategory={region.region_category} />
               ) : (
                  resultsPageContent
               )}
               <HSBTimeline dates={electionConfig.timeline_dates ?? []} documents={region.documents} region={region} />
               <IssueNotice issueReportDeadline={electionConfig.issue_report_deadline} />
            </div>
         </div>
      </LayoutMain>
   );
}
