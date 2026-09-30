import { faSearch } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useLingui } from "@lingui/react/macro";
import { type ReactNode, type SubmitEvent, useMemo, useState } from "react";
import Button from "@/elements/Button.tsx";
import type { RegionCategory } from "../api/types";
import { getRegionLabels } from "../utils/region";
import { lowercaseFirst } from "../utils/text";
import SearchAutocomplete, { type SearchListOption, useOptionMatcher } from "./SearchAutocomplete.tsx";

type Props = {
   regionCategory: RegionCategory;
   options: SearchListOption[];
   onSelect: (option: SearchListOption) => void;
   maxSuggestions?: number;
   children?: ReactNode;
};

const ALIASES: Record<string, string> = {
   "'s-Gravenhage": "Den Haag",
   "'s-Hertogenbosch": "Den Bosch",
   // Frisian official names, found by their Dutch counterparts
   Dantumadiel: "Dantumadeel",
   "De Fryske Marren": "De Friese Meren",
   "Noardeast-Fryslân": "Noordoost-Friesland",
   "Súdwest-Fryslân": "Zuidwest-Friesland",
   Tytsjerksteradiel: "Tietjerksteradeel",
};

export default function SearchBar({ regionCategory, options, onSelect, maxSuggestions = 8, children }: Props) {
   const { t } = useLingui();

   const SEARCH_CONFIG = {
      STEMBUREAU: {
         label: t`Zoek op naam, adres of stembureau-nummer`,
         placeholder: t`Bijv. Gymzaal de Boom`,
         submitBehavior: "first-match" as const,
      },
      GEMEENTE: {
         label: t`Zoek gemeente`,
         placeholder: t`Bijv. Zoetermeer`,
         submitBehavior: "exact-match" as const,
      },
      WATERSCHAP: {
         label: t`Zoek waterschap`,
         placeholder: t`Bijv. De Stichtse Rijnlanden`,
         submitBehavior: "exact-match" as const,
      },
      KIESKRING: {
         label: t`Zoek kieskring`,
         placeholder: t`Bijv. Leiden`,
         submitBehavior: "exact-match" as const,
      },
   } as const;

   const labels = getRegionLabels(regionCategory);
   const regionSingular = t(labels.singular);
   const regionInline = lowercaseFirst(regionSingular);
   const config = SEARCH_CONFIG[regionCategory as keyof typeof SEARCH_CONFIG] ?? {
      label: t`Zoek ${regionInline}`,
      placeholder: t`Bijv. ${regionSingular}`,
      submitBehavior: "exact-match" as const,
   };
   const { label, placeholder, submitBehavior } = config;
   const [query, setQuery] = useState("");
   const searchOptions = useMemo(
      () =>
         options.map((option) => {
            const alias = ALIASES[option.label];
            return alias ? { ...option, searchText: [option.searchText, alias].filter(Boolean).join(" ") } : option;
         }),
      [options],
   );

   const matches = useOptionMatcher();

   function selectOption(option: SearchListOption) {
      setQuery(option.label);
      onSelect(option);
   }

   // Reached by the button, or by Enter while no suggestion is highlighted; Enter on a highlighted one selects it.
   function handleSubmit(e: SubmitEvent<HTMLFormElement>) {
      e.preventDefault();
      const normalizedQuery = query.trim().toLowerCase();
      const option =
         options.find((option) => option.label.toLowerCase() === normalizedQuery) ??
         (submitBehavior === "first-match" ? searchOptions.find((option) => matches(option, query)) : undefined);

      if (option) {
         selectOption(option);
      }
   }

   return (
      <form className="mb-6 max-w-150" onSubmit={handleSubmit}>
         <div className="flex flex-row flex-wrap gap-x-2">
            <SearchAutocomplete
               label={label}
               placeholder={placeholder}
               value={query}
               onChange={setQuery}
               options={searchOptions}
               onSelect={selectOption}
               maxSuggestions={maxSuggestions}
            />
            <Button type="submit" aria-label={t`Zoeken`} variant="inverted">
               <FontAwesomeIcon icon={faSearch} />
            </Button>
            {children}
         </div>
      </form>
   );
}
