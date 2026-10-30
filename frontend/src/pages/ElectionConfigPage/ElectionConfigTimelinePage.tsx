import { useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, useLoaderData } from "react-router";
import ElectionConfigTabs from "@/components/ElectionConfigTabs.tsx";
import { LayoutMain } from "@/components/LayoutMain.tsx";
import PageTop from "@/components/PageTop.tsx";
import { ElectionTimelineSection } from "@/components/Timeline/ElectionTimelineSection.tsx";
import { electionConfigQuery } from "@/hooks/queries.ts";
import { useFormatters } from "@/utils/format.ts";

export function electionConfigTimelineLoader(queryClient: QueryClient) {
   return async ({ params }: LoaderFunctionArgs) => {
      const electionConfigQueryOptions = electionConfigQuery(params.electionConfigSlug);
      await queryClient.query(electionConfigQueryOptions);
      return { electionConfigQuery: electionConfigQueryOptions };
   };
}

type LoaderData = Awaited<ReturnType<ReturnType<typeof electionConfigTimelineLoader>>>;

export function ElectionConfigTimelinePage() {
   const { electionConfigQuery } = useLoaderData<LoaderData>();
   const { t } = useLingui();
   const { formatElectionDate } = useFormatters();
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery);

   const electionLabel = electionConfig.label;
   const electionDay = electionConfig.date ? formatElectionDate(electionConfig.date) : "";

   return (
      <LayoutMain
         title={t`Van stem tot uitslag ${electionLabel}`}
         description={t`Hoe de uitslag van de ${electionLabel} tot stand komt.`}
      >
         <PageTop
            title={t`Telresultaten ${electionLabel}`}
            subtitle={t`Verkiezingsdag: ${electionDay}`}
            breadcrumb={[{ href: "/", label: t`Home` }, { label: electionConfig.label }]}
            tabs={<ElectionConfigTabs electionConfig={electionConfig} />}
         />
         <ElectionTimelineSection electionConfig={electionConfig} />
      </LayoutMain>
   );
}
