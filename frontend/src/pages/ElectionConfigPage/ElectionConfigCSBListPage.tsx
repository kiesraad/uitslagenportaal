import { useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, type Params, useParams } from "react-router";
import type { ElectionConfig } from "@/api/types";
import ElectionConfigTabs from "@/components/ElectionConfigTabs.tsx";
import { LayoutMain } from "@/components/LayoutMain.tsx";
import { RegionList } from "@/components/ListPage/RegionList.tsx";
import PageTop from "@/components/PageTop.tsx";
import { CSBResultsComponent } from "@/components/ResultsPage/CSBResultsComponent.tsx";
import ResultsNotPublished from "@/components/ResultsPage/ResultsNotPublished.tsx";
import { electionConfigQuery, regionQuery, regionsQuery } from "@/hooks/queries.ts";
import { useFormatters } from "@/utils/format.ts";

/** The query for what the page lists: the one CSB's results, the CSBs, or nothing. */
function contentQueries(params: Params, electionConfig: ElectionConfig) {
   const singleCSB = electionConfig.single_csb;
   if (singleCSB) {
      return { singleCsbQuery: regionQuery({ ...params, regionSlug: singleCSB.slug }, "csb") };
   }
   // Single-CSB election whose staat region isn't imported yet: nothing to list.
   if (electionConfig.csb_type === "STAAT") {
      return {};
   }
   return { csbListQuery: regionsQuery(params, electionConfig.csb_type) };
}

export async function loadElectionConfigCSBList(client: QueryClient, { params }: Pick<LoaderFunctionArgs, "params">) {
   const electionConfig = await client.query(electionConfigQuery(params.electionConfigSlug));
   const { singleCsbQuery, csbListQuery } = contentQueries(params, electionConfig);

   if (singleCsbQuery) {
      await client.query(singleCsbQuery);
   } else if (csbListQuery) {
      await client.query(csbListQuery);
   }
}

type SingleCsbResultsProps = {
   electionConfig: ElectionConfig;
   regionQuery: ReturnType<typeof regionQuery>;
};

function SingleCsbResults({ electionConfig, regionQuery }: SingleCsbResultsProps) {
   const { data: csbRegion } = useSuspenseQuery(regionQuery);
   return <CSBResultsComponent electionConfig={electionConfig} region={csbRegion} />;
}

type CsbRegionListProps = {
   electionConfig: ElectionConfig;
   regionsQuery: ReturnType<typeof regionsQuery>;
};

function CsbRegionList({ electionConfig, regionsQuery }: CsbRegionListProps) {
   const { data: regions } = useSuspenseQuery(regionsQuery);

   return (
      <RegionList
         electionConfig={electionConfig}
         regions={regions}
         regionCategory={electionConfig.csb_type}
         isCsbList
         emptyPlaceholder
      />
   );
}

export default function ElectionConfigCSBListPage() {
   const params = useParams();
   const { t } = useLingui();
   const { formatElectionDate } = useFormatters();
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery(params.electionConfigSlug));
   const { singleCsbQuery, csbListQuery } = contentQueries(params, electionConfig);

   const electionLabel = electionConfig.label;
   const electionDay = electionConfig.date ? formatElectionDate(electionConfig.date) : "";

   return (
      <LayoutMain
         title={t`Telresultaten ${electionLabel}`}
         description={t`Bekijk de telresultaten per gemeente van de ${electionLabel}.`}
      >
         <PageTop
            title={t`Telresultaten ${electionLabel}`}
            subtitle={t`Verkiezingsdag: ${electionDay}`}
            breadcrumb={[
               { href: "/", label: t`Home` },
               {
                  label: electionConfig.label,
               },
            ]}
            tabs={<ElectionConfigTabs electionConfig={electionConfig} />}
         />
         {singleCsbQuery && <SingleCsbResults electionConfig={electionConfig} regionQuery={singleCsbQuery} />}
         {csbListQuery && <CsbRegionList electionConfig={electionConfig} regionsQuery={csbListQuery} />}
         {!singleCsbQuery && !csbListQuery && (
            <div className="page-main">
               <ResultsNotPublished regionName="" regionCategory="STAAT" />
            </div>
         )}
      </LayoutMain>
   );
}
