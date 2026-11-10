import type { QueryClient } from "@tanstack/react-query";
import type { LoaderFunctionArgs } from "react-router";
import { electionConfigQuery } from "../hooks/queries.ts";

export function reportIssueLoader(queryClient: QueryClient) {
   return async ({ params }: LoaderFunctionArgs) => {
      const electionConfigQueryOptions = electionConfigQuery(params.electionConfigSlug);
      await queryClient.query(electionConfigQueryOptions);

      return {
         electionConfigQuery: electionConfigQueryOptions,
      };
   };
}

export type ReportIssueLoaderData = Awaited<ReturnType<ReturnType<typeof reportIssueLoader>>>;
