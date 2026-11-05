import { QueryClient } from "@tanstack/react-query";
import { matchRoutes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { electionConfigsQuery } from "@/hooks/queries.ts";
import { loadRoot, routes } from "@/router.tsx";

function match(pathname: string) {
   const matches = matchRoutes(routes, pathname) ?? [];

   return {
      chain: matches.map((m) => m.route.id),
      params: matches.at(-1)?.params ?? {},
      // The root route is skipped: its loader loads the catalogue and prefetches the Footer's election list, which is not page data.
      // Page loaders live inside `lazy`, so a single lazy leaf means data is fetched once.
      loaders: matches.slice(1).filter((m) => m.route.lazy).length,
   };
}

describe("router", () => {
   it.each([
      ["/", "HomePage"],
      ["/ab2023/csb/kieskring-1/resultaten/vvd", "CSBPartyResultsPage"],
      // A static segment outranks the stembureau parameter it sits beside.
      ["/ab2023/gsb/utrecht/csb/csb-1/resultaten", "MunicipalityResultsPage"],
      ["/ab2023/gsb/utrecht/csb/csb-1/sb-3", "PollingStationResultsPage"],
      ["/ab2023/onzin", "NotFoundPageNested"],
   ])("%s renders %s", (pathname, expected) => {
      expect(match(pathname).chain.at(-1)).toBe(expected);
   });

   it("gathers the parameters of every level", () => {
      expect(match("/ab2023/gsb/utrecht/csb/csb-1/sb-3/vvd").params).toEqual({
         electionConfigSlug: "ab2023",
         regionSlug: "utrecht",
         csbSlug: "csb-1",
         pollingStationSlug: "sb-3",
         partySlug: "vvd",
      });
   });

   // Each page owns its own loader, so no ancestor may fetch the same data again.
   it.each([
      ["/"],
      ["/ab2023/gsb"],
      ["/ab2023/csb"],
      ["/ab2023/csb/kieskring-1"],
      ["/ab2023/csb/kieskring-1/resultaten"],
      ["/ab2023/csb/kieskring-1/resultaten/vvd"],
      ["/ab2023/gsb/utrecht/csb/csb-1"],
      ["/ab2023/gsb/utrecht/csb/csb-1/resultaten"],
      ["/ab2023/gsb/utrecht/csb/csb-1/resultaten/vvd"],
      ["/ab2023/gsb/utrecht/csb/csb-1/sb-3"],
      ["/ab2023/gsb/utrecht/csb/csb-1/sb-3/vvd"],
   ])("loads the data of %s exactly once", (pathname) => {
      expect(match(pathname).loaders).toBe(1);
   });
});

describe("loadRoot", () => {
   afterEach(() => vi.unstubAllGlobals());

   it("resolves with the locale while the election list never arrives", async () => {
      vi.stubGlobal(
         "fetch",
         vi.fn(() => new Promise<Response>(() => {})),
      );

      await expect(loadRoot(new QueryClient())).resolves.toEqual({ locale: expect.stringMatching(/^(nl|en)$/) });
   });

   it("resolves with the locale and swallows the rejection when the election list fails to load", async () => {
      vi.stubGlobal(
         "fetch",
         vi.fn(() => Promise.reject(new Error("network down"))),
      );
      const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

      await expect(loadRoot(client)).resolves.toEqual({ locale: expect.stringMatching(/^(nl|en)$/) });
      await vi.waitFor(() => expect(client.getQueryState(electionConfigsQuery().queryKey)?.status).toBe("error"));
   });
});
