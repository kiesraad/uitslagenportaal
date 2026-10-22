import { faChevronRight, faInfo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Plural, Trans, useLingui } from "@lingui/react/macro";
import { type PropsWithChildren, useEffect, useMemo, useRef, useState } from "react";
import { Button, Popover } from "react-aria-components";
import { Link, useNavigate } from "react-router";
import { twMerge } from "tailwind-merge";
import type { ElectionConfig, Region, RegionCategory } from "../../api/types";
import { useFormatters } from "../../utils/format";
import { formatStationLabel, getRegionLabels } from "../../utils/region";
import { appRoutes } from "../../utils/routes";
import { lowercaseFirst } from "../../utils/text";
import type { SearchListOption } from "../SearchAutocomplete";
import SearchBar from "../SearchBar";
import { RegionListNotAvailable } from "./RegionListNotAvailable";

function compareByStationNumber(a: SearchListOption, b: SearchListOption): number {
   return (a.stationNumber ?? 0) - (b.stationNumber ?? 0);
}

type Props = {
   electionConfig: ElectionConfig;
   regions: Region[] | undefined;
   regionCategory: RegionCategory;
   parentRegionSlug?: string;
   parentCsbSlug?: string;
   regionTitle?: string;
   emptyPlaceholder?: boolean;
};

export function RegionList({
   electionConfig,
   regions,
   regionCategory,
   parentRegionSlug,
   parentCsbSlug,
   regionTitle,
   emptyPlaceholder = false,
}: Props) {
   const navigate = useNavigate();
   const { t } = useLingui();
   const { collator } = useFormatters();
   const regionInline = lowercaseFirst(t(getRegionLabels(regionCategory).singular));

   function navigateToGemeente(option: SearchListOption) {
      navigate(appRoutes.municipalityPollingstationList(electionConfig.slug ?? "", option.id, option.csbSlug));
   }

   function navigateToPollingStation(option: SearchListOption) {
      if (!parentRegionSlug) return;
      navigate(appRoutes.pollingStationResults(electionConfig.slug, parentRegionSlug, option.id, parentCsbSlug));
   }

   const REGION_DETAIL_ROUTE_BUILDERS: Partial<Record<RegionCategory, typeof appRoutes.csbResults>> = {
      WATERSCHAP: appRoutes.csbResults,
      PROVINCIE: appRoutes.csbResults,
      KIESKRING: appRoutes.hsbResults,
   };

   function getRegionRoute(option: SearchListOption) {
      if (regionCategory === "STEMBUREAU" && parentRegionSlug) {
         return appRoutes.pollingStationResults(electionConfig.slug, parentRegionSlug, option.id, parentCsbSlug);
      }
      const detailRoute = REGION_DETAIL_ROUTE_BUILDERS[regionCategory];
      if (detailRoute) {
         return detailRoute(electionConfig.slug, option.id);
      }
      return appRoutes.municipalityPollingstationList(electionConfig.slug, option.id, option.csbSlug);
   }

   let navigateToRegion: (option: SearchListOption) => void;
   if (regionCategory === "STEMBUREAU") {
      navigateToRegion = navigateToPollingStation;
   } else if (regionCategory in REGION_DETAIL_ROUTE_BUILDERS) {
      navigateToRegion = (option) => navigate(getRegionRoute(option));
   } else {
      navigateToRegion = navigateToGemeente;
   }

   const isPollingStationList = regionCategory === "STEMBUREAU";

   const regionOptions: SearchListOption[] = useMemo(() => {
      const visibleRegions = (regions ?? []).filter((region) => region.region_name);

      const nameCounts = visibleRegions.reduce<Record<string, number>>((counts, region) => {
         counts[region.region_name] = (counts[region.region_name] ?? 0) + 1;
         return counts;
      }, {});

      return visibleRegions.map((region) => {
         const isAmbiguous = nameCounts[region.region_name] > 1 && Boolean(region.csb_name);
         const name = isAmbiguous ? `${region.region_name} - ${region.csb_name}` : region.region_name;
         const stationNumber = isPollingStationList ? (region.station_number ?? undefined) : undefined;
         return {
            id: region.slug,
            label: formatStationLabel(name, stationNumber),
            sortName: region.region_name,
            stationNumber,
            sameLocationStationNumbers: isPollingStationList
               ? (region.same_location_stations ?? []).flatMap((station) => station.station_number ?? [])
               : undefined,
            csbSlug: region.csb_slug ?? undefined,
         };
      });
   }, [regions, isPollingStationList]);

   const sortedPollingStations = useMemo(() => regionOptions.slice().sort(compareByStationNumber), [regionOptions]);

   const regionsByLetter = useMemo(() => {
      const grouped = regionOptions.reduce<Record<string, SearchListOption[]>>((grouped, option) => {
         const sortName = option.sortName ?? option.label;
         // handle 's-Gravenhage and 's-Hertogenbosch
         const name = sortName.startsWith("'s-") ? sortName.slice(3) : sortName;
         const letter = name[0].toUpperCase();
         grouped[letter] ??= [];
         grouped[letter].push(option);
         return grouped;
      }, {});

      return Object.entries(grouped).sort(([a], [b]) => collator.compare(a, b));
   }, [regionOptions, collator]);

   if (emptyPlaceholder && regionOptions.length === 0) {
      return (
         <div className="page-main">
            <RegionListNotAvailable regionCategory={regionCategory} />
         </div>
      );
   }

   return (
      <div className="page-main">
         {isPollingStationList && (
            <h2 className="mb-4">
               <Plural
                  value={sortedPollingStations.length}
                  one={`# stembureau in ${regionTitle}`}
                  other={`# stembureaus in ${regionTitle}`}
               />
            </h2>
         )}

         <SearchBar regionCategory={regionCategory} options={regionOptions} onSelect={navigateToRegion} />

         {!isPollingStationList && <h2 className="mb-4 max-sm:max-w-70">{t`Vind een ${regionInline} van A tot Z`}</h2>}

         {isPollingStationList ? (
            <SearchList>
               {sortedPollingStations.map((station) => (
                  <ListOptionLink
                     key={`${station.id}-${station.csbSlug ?? ""}`}
                     listOption={station}
                     to={getRegionRoute(station)}
                  />
               ))}
            </SearchList>
         ) : (
            regionsByLetter.map(([letter, municipalities]) => (
               <div key={letter} className="mb-6">
                  <h3 className="py-2 font-sans max-sm:sticky max-sm:top-0 max-sm:bg-white/75">{letter}</h3>
                  <SearchList>
                     {municipalities.map((municipality) => (
                        <ListOptionLink
                           key={`${municipality.id}-${municipality.csbSlug ?? ""}`}
                           listOption={municipality}
                           to={getRegionRoute(municipality)}
                        />
                     ))}
                  </SearchList>
               </div>
            ))
         )}
      </div>
   );
}

function SearchList({ children }: PropsWithChildren) {
   return <ul className="mb-5 grid max-w-2xl grid-cols-[max-content_auto_max-content]">{children}</ul>;
}

function ListOptionLink({ listOption, to }: { listOption: SearchListOption; to: string }) {
   const { t } = useLingui();
   const { locale } = useFormatters();
   const name = listOption.stationNumber != null ? (listOption.sortName ?? listOption.label) : listOption.label;
   const sameLocationNumbers = listOption.sameLocationStationNumbers ?? [];
   const isDoubleStation = sameLocationNumbers.length > 0;
   const otherNumbers = new Intl.ListFormat(locale).format(sameLocationNumbers.map(String));
   return (
      <li className="relative col-span-3 grid grid-cols-subgrid odd:bg-blue-50">
         <Link
            to={to}
            className="col-span-3 grid min-h-18 grid-cols-subgrid items-center px-6 hover:bg-blue-100 hover:no-underline"
         >
            <span className={twMerge(listOption.stationNumber && "pr-2 font-light text-gray-700")}>
               {listOption.stationNumber}
               {/* Grid items have no whitespace between them, so screen readers would glue the number to the name. */}
               {listOption.stationNumber !== undefined && <span className="sr-only">&nbsp;</span>}
            </span>
            <span className={twMerge("py-3", isDoubleStation && "pr-12")}>
               <span className="underline">{name}</span>
               {isDoubleStation && (
                  <span className="sr-only">
                     , <Trans>Dubbel stembureau</Trans>, <Trans>Ook stembureau {otherNumbers} op deze locatie</Trans>
                  </span>
               )}
            </span>
            <span>
               <FontAwesomeIcon icon={faChevronRight} />
            </span>
         </Link>
         {/* A sibling of the link, not a child: a button may not sit inside a link. */}
         {isDoubleStation && (
            <DoubleStationInfo label={t`Uitleg dubbel stembureau ${name}`} otherNumbers={otherNumbers} />
         )}
      </li>
   );
}

/** Info button that opens on hover, click, tap or Enter; closes on Escape, a click outside or the pointer leaving. */
function DoubleStationInfo({ label, otherNumbers }: { label: string; otherNumbers: string }) {
   const triggerRef = useRef<HTMLButtonElement>(null);
   const popoverRef = useRef<HTMLDivElement>(null);
   const isPointerOver = useRef(false);
   const closeTimer = useRef<number | undefined>(undefined);
   const [isOpen, setOpen] = useState(false);

   function open() {
      window.clearTimeout(closeTimer.current);
      setOpen(true);
   }

   // The delay lets the pointer cross the gap onto the popover without it closing (WCAG 1.4.13).
   function closeSoon() {
      window.clearTimeout(closeTimer.current);
      closeTimer.current = window.setTimeout(() => setOpen(false), 300);
   }

   function pointerEnter() {
      isPointerOver.current = true;
      open();
   }

   function pointerLeave() {
      isPointerOver.current = false;
      closeSoon();
   }

   useEffect(() => {
      if (!isOpen) return;
      const onKeyDown = (event: KeyboardEvent) => {
         if (event.key === "Escape") setOpen(false);
      };
      const onPointerDown = (event: PointerEvent) => {
         const target = event.target as Node;
         if (!triggerRef.current?.contains(target) && !popoverRef.current?.contains(target)) setOpen(false);
      };
      document.addEventListener("keydown", onKeyDown);
      document.addEventListener("pointerdown", onPointerDown);
      return () => {
         document.removeEventListener("keydown", onKeyDown);
         document.removeEventListener("pointerdown", onPointerDown);
      };
   }, [isOpen]);

   useEffect(() => () => window.clearTimeout(closeTimer.current), []);

   return (
      <>
         <Button
            ref={triggerRef}
            aria-label={label}
            aria-expanded={isOpen}
            onPress={open}
            onHoverStart={pointerEnter}
            onHoverEnd={pointerLeave}
            onBlur={() => !isPointerOver.current && setOpen(false)}
            className="absolute top-1/2 right-14 flex size-6 -translate-y-1/2 cursor-pointer items-center justify-center rounded-xs bg-blue text-white focus-visible:outline-2 focus-visible:outline-blue focus-visible:outline-offset-2"
         >
            <FontAwesomeIcon icon={faInfo} className="text-[0.7rem]" />
         </Button>
         {/* Non-modal, so opening on hover neither moves focus nor hides the rest of the page. */}
         <Popover
            triggerRef={triggerRef}
            isOpen={isOpen}
            onOpenChange={setOpen}
            isNonModal
            placement="top end"
            className="max-w-xs rounded-xs border border-blue-200 bg-white text-gray-700 text-sm shadow-md"
         >
            <div ref={popoverRef} onPointerEnter={pointerEnter} onPointerLeave={pointerLeave} className="px-3 py-2">
               <p>
                  <Trans>Dubbel stembureau</Trans>
               </p>
               <p>
                  <Trans>Ook stembureau {otherNumbers} op deze locatie</Trans>
               </p>
            </div>
         </Popover>
      </>
   );
}
