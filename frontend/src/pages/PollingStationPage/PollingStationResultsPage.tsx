import { Trans, useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { Link, type LoaderFunctionArgs, useLoaderData } from "react-router";
import { SBTimeline } from "@/components/Timeline/SBTimeline.tsx";
import { LayoutMain } from "../../components/LayoutMain.tsx";
import PageTop from "../../components/PageTop";
import RegionResultsContent from "../../components/ResultsPage/RegionResultsContent";
import ResultsPageColumns from "../../components/ResultsPage/ResultsPageColumns";
import { electionConfigQuery, regionQuery } from "../../hooks/queries";
import { useFormatters } from "../../utils/format";
import { formatStationLabel, getCsbCrumb } from "../../utils/region";
import { appRoutes } from "../../utils/routes";

/** The stembureau and the gemeente it belongs to, for both stembureau pages. */
export function pollingStationLoader(queryClient: QueryClient) {
   return async ({ params }: LoaderFunctionArgs) => {
      const electionConfigQueryOptions = electionConfigQuery(params.electionConfigSlug);
      const regionQueryOptions = regionQuery(params, "gsb");
      // The stembureau is the region being fetched here; the gemeente in the URL is its parent.
      const pollingStationQueryOptions = regionQuery(
         {
            electionConfigSlug: params.electionConfigSlug,
            regionSlug: params.pollingStationSlug,
            csbSlug: params.csbSlug,
            parentRegionSlug: params.regionSlug,
         },
         "sb",
      );

      await Promise.all([
         queryClient.query(electionConfigQueryOptions),
         queryClient.query(regionQueryOptions),
         queryClient.query(pollingStationQueryOptions),
      ]);

      return {
         electionConfigQuery: electionConfigQueryOptions,
         regionQuery: regionQueryOptions,
         pollingStationQuery: pollingStationQueryOptions,
      };
   };
}

export type PollingStationLoaderData = Awaited<ReturnType<ReturnType<typeof pollingStationLoader>>>;

export default function PollingStationResultsPage() {
   const { electionConfigQuery, regionQuery, pollingStationQuery } = useLoaderData<PollingStationLoaderData>();
   const { t } = useLingui();
   const { formatDate, locale } = useFormatters();
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

   const stationName = pollingStation.region_name;
   const stationLabel = formatStationLabel(stationName, pollingStation.station_number);
   const regionName = region.region_name;
   // No publication date until the region's results have been imported; the line is then omitted.
   const publishedAt = region.results_available_at ? formatDate(region.results_available_at) : null;
   const pageTitle = `${t`Telresultaten stembureau`}\n${stationName}`;
   const documentTitle = t`Telresultaten stembureau – ${stationName}`;

   const sameLocationStations = (pollingStation.same_location_stations ?? []).filter(
      (station) => station.station_number != null,
   );
   const otherStationLinks = new Intl.ListFormat(locale)
      .formatToParts(sameLocationStations.map((station) => String(station.station_number)))
      .map((part) => {
         if (part.type === "literal") return part.value;
         const stationNumber = part.value;
         const station = sameLocationStations.find(({ station_number }) => String(station_number) === stationNumber);
         return (
            <Link
               key={stationNumber}
               to={appRoutes.pollingStationResults(electionConfig.slug, region.slug, station?.slug ?? "", csbSlug)}
            >
               {t`stembureau ${stationNumber}`}
            </Link>
         );
      });

   return (
      <LayoutMain title={documentTitle} description={documentTitle}>
         <PageTop
            title={pageTitle}
            subtitle={publishedAt ? t`Geplaatst op: ${publishedAt}` : undefined}
            breadcrumb={[
               { href: appRoutes.home(), label: t`Home` },
               { href: appRoutes.electionConfigMunicipalityList(electionConfig.slug), label: electionConfig.label },
               getCsbCrumb(region, electionConfig.slug),
               { href: municipalityPollingstationListRoute, label: t`Gemeente ${regionName}` },
               { label: stationLabel },
            ]}
         />
         <ResultsPageColumns
            previewUrl={pollingStation.certified_document_preview_url}
            documentUrl={pollingStation.certified_document_url}
         >
            <RegionResultsContent
               intro={t`De gemeente typt de telgegevens van alle stembureaus over in de uitslagensoftware. Zo kunnen alle stemmen worden opgeteld. Hieronder zie je hoe de gegevens van dit stembureau zijn overgenomen in de uitslagensoftware.`}
               notice={
                  sameLocationStations.length > 0 && (
                     <>
                        <h2 className="h4">
                           <Trans>Dit is een dubbel stembureau</Trans>
                        </h2>
                        <p>
                           <Trans>Op dezelfde locatie zit ook {otherStationLinks}.</Trans>
                        </p>
                     </>
                  )
               }
               voteCounts={pollingStation.vote_counts}
               turnoutVotes={pollingStation.voter_turnout_counts}
               issueReportDeadline={electionConfig.issue_report_deadline}
               notPublishedRegionName={region.region_name}
               notPublishedRegionCategory={region.region_category}
               timeline={<SBTimeline variant={pollingStation.timeline_variant} dates={electionConfig.timeline_dates} />}
            />
         </ResultsPageColumns>
      </LayoutMain>
   );
}
