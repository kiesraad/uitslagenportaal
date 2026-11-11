import { useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, useParams } from "react-router";
import ElectionConfigTabs from "@/components/ElectionConfigTabs.tsx";
import { LayoutMain } from "@/components/LayoutMain.tsx";
import PageTop from "@/components/PageTop.tsx";
import { ElectionTimelineSection } from "@/components/Timeline/ElectionTimelineSection.tsx";
import { electionConfigQuery } from "@/hooks/queries.ts";
import { queryClient } from "@/queryClient.ts";
import { useFormatters } from "@/utils/format.ts";
import type { Route } from "./+types/ElectionConfigTimelinePage";

export async function loadElectionConfigTimeline(client: QueryClient, { params }: Pick<LoaderFunctionArgs, "params">) {
   await client.query(electionConfigQuery(params.electionConfigSlug));
}

export const clientLoader = (args: Route.ClientLoaderArgs) => loadElectionConfigTimeline(queryClient, args);

export default function ElectionConfigTimelinePage() {
   const params = useParams();
   const { t } = useLingui();
   const { formatElectionDate } = useFormatters();
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery(params.electionConfigSlug));

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
