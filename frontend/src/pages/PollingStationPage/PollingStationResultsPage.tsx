import { Trans, useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { Link, type LoaderFunctionArgs, type Params, useParams } from "react-router";
import { SBTimeline } from "@/components/Timeline/SBTimeline.tsx";
import { LayoutMain } from "../../components/LayoutMain.tsx";
import PageTop from "../../components/PageTop";
import RegionResultsContent from "../../components/ResultsPage/RegionResultsContent";
import ResultsPageColumns from "../../components/ResultsPage/ResultsPageColumns";
import { electionConfigQuery, regionQuery } from "../../hooks/queries";
import { useFormatters } from "../../utils/format";
import { formatStationLabel, getCsbCrumb, getRegionLabels } from "../../utils/region";
import { appRoutes } from "../../utils/routes";

/** The election, the gemeente and the stembureau, for both stembureau pages. */
export function pollingStationQueries(params: Params) {
   return {
      electionConfig: electionConfigQuery(params.electionConfigSlug),
      region: regionQuery(params, "gsb"),
      // The stembureau is the region being fetched here; the gemeente in the URL is its parent.
      pollingStation: regionQuery(
         {
            electionConfigSlug: params.electionConfigSlug,
            regionSlug: params.pollingStationSlug,
            csbSlug: params.csbSlug,
            parentRegionSlug: params.regionSlug,
         },
         "sb",
      ),
   };
}

export async function loadPollingStationResults(client: QueryClient, { params }: Pick<LoaderFunctionArgs, "params">) {
   const queries = pollingStationQueries(params);
   await Promise.all([
      client.query(queries.electionConfig),
      client.query(queries.region),
      client.query(queries.pollingStation),
   ]);
}

export default function PollingStationResultsPage() {
   const queries = pollingStationQueries(useParams());
   const { t } = useLingui();
   const { formatDate, locale } = useFormatters();
   const { data: electionConfig } = useSuspenseQuery(queries.electionConfig);
   const { data: region } = useSuspenseQuery(queries.region);
   const { data: pollingStation } = useSuspenseQuery(queries.pollingStation);

   const csbSlug = region.csb?.slug;
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
   const regionWithArticle = t(getRegionLabels("STEMBUREAU").withArticle);

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
               getCsbCrumb(region, electionConfig),
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
               reports={{
                  description: t`De getallen hierboven laten zien hoe de resultaten van ${regionWithArticle} worden meegeteld in de uitslag. Ze komen uit de uitslagensoftware. Ze zijn door de gemeente overgetypt uit onderstaande documenten. `,
                  documents: pollingStation.documents,
               }}
               issueReportDeadline={electionConfig.issue_report_deadline}
               notPublishedRegionName={region.region_name}
               notPublishedRegionCategory={region.region_category}
               timeline={
                  <SBTimeline
                     variant={pollingStation.timeline_variant}
                     dates={electionConfig.timeline_dates}
                     documents={pollingStation.documents}
                     region={pollingStation}
                     municipality={region}
                  />
               }
            />
         </ResultsPageColumns>
      </LayoutMain>
   );
}
