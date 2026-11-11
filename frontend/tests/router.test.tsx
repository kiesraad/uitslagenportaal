import type { RouteConfigEntry } from "@react-router/dev/routes";
import { QueryClient } from "@tanstack/react-query";
import { matchRoutes, type RouteObject } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { electionConfigsQuery } from "@/hooks/queries.ts";
import { loadRoot } from "@/root.tsx";
import routeConfig from "@/routes.ts";

type TestRoute = RouteObject & { file?: string };

// `matchRoutes` wants the shape of a data router; the route config only differs in naming its module `file`.
function toRoutes(entries: RouteConfigEntry[]): TestRoute[] {
   return entries.map(({ id, path, index, file, children }) => ({
      id,
      path,
      index,
      file,
      children: children && toRoutes(children),
   })) as TestRoute[];
}

// The framework mounts routes.ts below root.tsx.
const routes: TestRoute[] = [{ id: "root", path: "/", children: toRoutes(routeConfig as RouteConfigEntry[]) }];

function match(pathname: string) {
   const matches = matchRoutes(routes, pathname) ?? [];

   return {
      chain: matches.map((m) => m.route.id),
      params: matches.at(-1)?.params ?? {},
      // The root route is skipped: its loader loads the catalogue and prefetches the Footer's election list, which is not page data.
      // Parameter levels render a bare `RouteOutlet` without a loader, so a single other module means data is fetched once.
      pages: matches.slice(1).filter((m) => !m.route.file?.endsWith("RouteOutlet.tsx")).length,
   };
}

describe("router", () => {
   it.each([
      ["/", "HomePage"],
      ["/ab2023/csb/kieskring-1/resultaten/vvd", "CSBPartyResultsPage"],
      // A static segment outranks the stembureau parameter it sits beside.
      ["/ab2023/gsb/utrecht/csb/csb-1/resultaten", "MunicipalityResultsPage"],
      ["/ab2023/gsb/utrecht/csb/csb-1/sb-3", "PollingStationResultsPage"],
      // A GR gemeente has no CSB above it.
      ["/gr2026/gsb/ede", "MunicipalityPollingstationListPageWithoutCsb"],
      ["/gr2026/gsb/ede/resultaten", "MunicipalityResultsPageWithoutCsb"],
      ["/gr2026/gsb/ede/sb-3/vvd", "PollingStationPartyResultsPageWithoutCsb"],
      ["/ab2023/onzin", "NotFoundPageNested"],
      ["/ab2023", "NotFoundPage"],
      ["/ab2023/van-stem-tot-uitslag", "ElectionConfigTimelinePage"],
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
      ["/gr2026/gsb/ede"],
      ["/gr2026/gsb/ede/sb-3/vvd"],
   ])("loads the data of %s exactly once", (pathname) => {
      expect(match(pathname).pages).toBe(1);
   });
});

function routeFiles(entries: RouteConfigEntry[]): string[] {
   return entries.flatMap((entry) => [entry.file, ...routeFiles(entry.children ?? [])]);
}

// A page without a clientLoader would render without its data in the cache.
describe("route modules", () => {
   const withoutLoader = ["components/RouteOutlet.tsx", "pages/NotFoundPage.tsx"];
   const pageFiles = [...new Set(routeFiles(routeConfig as RouteConfigEntry[]))].filter(
      (file) => !withoutLoader.includes(file),
   );

   it.each(pageFiles)("%s exports a clientLoader", async (file) => {
      const module = await import(`../src/${file}`);
      expect(module.clientLoader).toBeTypeOf("function");
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
