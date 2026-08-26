import { matchRoutes } from "react-router";
import { describe, expect, it } from "vitest";
import { routes } from "@/router.tsx";

function match(pathname: string) {
   const matches = matchRoutes(routes, pathname) ?? [];

   return {
      chain: matches.map((m) => (m.route as { Component?: { name: string } }).Component?.name),
      params: matches.at(-1)?.params ?? {},
      loaders: matches.filter((m) => m.route.loader).length,
   };
}

describe("router", () => {
   it.each([
      ["/", "HomePage"],
      ["/ab2023/csb/kieskring-1/resultaten/vvd", "CSBPartyResultsPage"],
      // A static segment outranks the stembureau parameter it sits beside.
      ["/ab2023/gsb/utrecht/csb/csb-1/resultaten", "MunicipalityResultsPage"],
      ["/ab2023/gsb/utrecht/csb/csb-1/sb-3", "PollingStationResultsPage"],
      ["/ab2023/onzin", "NotFoundPage"],
   ])("%s renders %s", (pathname, expected) => {
      expect(match(pathname).chain.at(-1)).toBe(expected);
   });

   it("wraps only its own routes in the municipality layout", () => {
      expect(match("/ab2023/gsb/utrecht/csb/csb-1/resultaten").chain).toContain("MunicipalityPageLayout");
      expect(match("/ab2023/gsb/utrecht/csb/csb-1/sb-3").chain).not.toContain("MunicipalityPageLayout");
   });

   it("gathers the parameters of every level and loads the election config once", () => {
      const { params, loaders } = match("/ab2023/gsb/utrecht/csb/csb-1/sb-3/vvd");

      expect(params).toEqual({
         electionConfigSlug: "ab2023",
         regionSlug: "utrecht",
         csbSlug: "csb-1",
         pollingStationSlug: "sb-3",
         partySlug: "vvd",
      });
      expect(loaders).toBe(1);
   });
});
