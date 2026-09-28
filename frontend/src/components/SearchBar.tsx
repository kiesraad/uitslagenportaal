import { faSearch } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Plural, useLingui } from "@lingui/react/macro";
import { type FocusEvent, type ReactNode, type SubmitEvent, useMemo, useState } from "react";
import { useFilter } from "react-aria-components";
import Button from "@/elements/Button.tsx";
import type { RegionCategory } from "../api/types";
import { getRegionLabels } from "../utils/region";
import { lowercaseFirst } from "../utils/text";
import SearchAutocomplete, { type SearchListOption } from "./SearchAutocomplete.tsx";

type Props = {
   regionCategory: RegionCategory;
   options: SearchListOption[];
   onSelect: (option: SearchListOption) => void;
   maxSuggestions?: number;
   children?: ReactNode;
};

export default function SearchBar({ regionCategory, options, onSelect, maxSuggestions = 8, children }: Props) {
   const { t } = useLingui();
   const { contains } = useFilter({ sensitivity: "base" });

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
         aliases: {
            "'s-Gravenhage": ["Den Haag"],
            "'s-Hertogenbosch": ["Den Bosch"],
         },
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

   const ALIASES: Record<string, string> = {
      "'s-Gravenhage": "Den Haag",
      "'s-Hertogenbosch": "Den Bosch",
      // Frisian official names, found by their Dutch counterparts
      Dantumadiel: "Dantumadeel",
      "De Fryske Marren": "De Friese Meren",
      "Noardeast-Fryslân": "Noordoost-Friesland",
      "Súdwest-Fryslân": "Zuidwest-Friesland",
      Tytsjerksteradiel: "Tietjerksteradeel",
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
   const [open, setOpen] = useState(false);
   const searchOptions = useMemo(() => {
      return options.map((option) => {
         option.searchText = [option?.searchText, ALIASES?.[option.label]].filter((option) => option).join(" ");
         return option;
      });
   }, [ALIASES, options]);

   const suggestions = useMemo(() => {
      const normalizedQuery = query.trim();

      if (normalizedQuery.length === 0) {
         return [];
      }

      return searchOptions
         .filter((option) => contains(`${option.label} ${option.searchText ?? ""}`, normalizedQuery))
         .slice(0, maxSuggestions);
   }, [maxSuggestions, searchOptions, query, contains]);
   const isOpen = open && suggestions.length > 0;

   function selectOption(option: SearchListOption) {
      setQuery(option.label);
      setOpen(false);
      onSelect(option);
   }

   function handleChange(value: string) {
      setQuery(value);
      setOpen(true);
   }

   // Reached by the button, or by Enter while no suggestion is highlighted; Enter on a highlighted one selects it.
   function handleSubmit(e: SubmitEvent<HTMLFormElement>) {
      e.preventDefault();
      const normalizedQuery = query.trim().toLowerCase();
      const option =
         options.find((option) => option.label.toLowerCase() === normalizedQuery) ??
         (submitBehavior === "first-match" ? suggestions[0] : undefined);

      if (option) {
         selectOption(option);
      }
   }

   // Clicking a suggestion focuses the listbox, so only close once focus leaves the form altogether.
   function handleBlur(e: FocusEvent<HTMLFormElement>) {
      if (!e.currentTarget.contains(e.relatedTarget)) {
         setOpen(false);
      }
   }

   return (
      // biome-ignore lint/a11y/noNoninteractiveElementInteractions: onBlur only tracks focus leaving the controls inside.
      <form className="mb-6 max-w-150" onSubmit={handleSubmit} onBlur={handleBlur}>
         <div className="flex flex-row flex-wrap gap-x-2">
            <SearchAutocomplete
               label={label}
               placeholder={placeholder}
               value={query}
               onChange={handleChange}
               options={suggestions}
               isOpen={isOpen}
               onSelect={selectOption}
            />
            <Button type="submit" aria-label={t`Zoeken`} variant="inverted">
               <FontAwesomeIcon icon={faSearch} />
            </Button>
            {children}
         </div>
         {/* Rendered always, so screen readers pick up changes to its text. */}
         <div role="status" className="sr-only">
            {open && query.trim().length > 0 && (
               <Plural value={suggestions.length} _0="Geen resultaten" one="# resultaat" other="# resultaten" />
            )}
         </div>
      </form>
   );
}
