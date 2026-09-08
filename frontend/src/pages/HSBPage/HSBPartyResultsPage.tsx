import { Trans, useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, useLoaderData } from "react-router";
import { LayoutMain } from "../../components/LayoutMain.tsx";
import PageTop from "../../components/PageTop.tsx";
import IssueNotice from "../../components/ResultsPage/IssueNotice.tsx";
import PartyVoteMatrixTable from "../../components/ResultsPage/PartyVoteMatrixTable.tsx";
import ResultsNotPublished from "../../components/ResultsPage/ResultsNotPublished.tsx";
import ResultsPageIndex from "../../components/ResultsPage/ResultsPageIndex";
import ResultsTimeline from "../../components/ResultsPage/ResultsTimeline.tsx";
import { electionConfigQuery, hsbPartyVoteMatrixQuery, regionQuery } from "../../hooks/queries.ts";
import { useFormatters } from "../../utils/format.ts";
import { getRegionLabels } from "../../utils/region.ts";
import { appRoutes } from "../../utils/routes.ts";
import { getPartyVoteCount } from "../../utils/voteCounts.ts";

export function hsbPartyResultsLoader(queryClient: QueryClient) {
   return async ({ params }: LoaderFunctionArgs) => {
      const electionConfigQueryOptions = electionConfigQuery(params.electionConfigSlug);
      const regionQueryOptions = regionQuery(params);

      const [, region] = await Promise.all([
         queryClient.ensureQueryData(electionConfigQueryOptions),
         queryClient.ensureQueryData(regionQueryOptions),
      ]);

      const partyVoteMatrixQueryOptions = hsbPartyVoteMatrixQuery(
         region.election_slug,
         params.regionSlug,
         params.partySlug,
      );
      await queryClient.ensureQueryData(partyVoteMatrixQueryOptions);

      return {
         electionConfigQuery: electionConfigQueryOptions,
         regionQuery: regionQueryOptions,
         partyVoteMatrixQuery: partyVoteMatrixQueryOptions,
      };
   };
}

type LoaderData = Awaited<ReturnType<ReturnType<typeof hsbPartyResultsLoader>>>;

export function HSBPartyResultsPage() {
   const { electionConfigQuery, regionQuery, partyVoteMatrixQuery } = useLoaderData<LoaderData>();
   const { t } = useLingui();
   const { formatDate } = useFormatters();
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery);
   const { data: region } = useSuspenseQuery(regionQuery);
   const { data: partyVoteMatrix } = useSuspenseQuery(partyVoteMatrixQuery);

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
            <h2 className="text-lg mb-4.5 font-medium">
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
            <PartyVoteMatrixTable matrix={partyVoteMatrix} />
         </section>
      </>
   );

   return (
      <LayoutMain title={t`Resultaten`}>
         <PageTop
            title={`${t`Telresultaten ${regionType} ${regionName}`}\n ${partyName}`}
            subtitle={publishedAt ? t`Geplaatst op: ${publishedAt}` : undefined}
            breadcrumb={[
               { href: appRoutes.home(), label: t`Home` },
               {
                  href: appRoutes.electionConfigMunicipalityList(electionConfig.slug),
                  label: electionConfig.label,
               },
               { href: appRoutes.hsbResults(electionConfig.slug, region.slug), label: region.region_name },
               { href: appRoutes.hsbPartyResults(electionConfig.slug, region.slug, partySlug), label: partyName },
            ]}
         />
         <div className="page-main">
            <div className="page-space-3 party-vote-matrix-page">
               {!hasResults ? <ResultsNotPublished regionLabel={region.region_name} /> : resultsPageContent}
               <ResultsTimeline variant={region.timeline_variant} entries={electionConfig.timeline_entries ?? []} />
               <IssueNotice issueReportDeadline={electionConfig.issue_report_deadline} />
            </div>
         </div>
      </LayoutMain>
   );
}
