import { faSearch } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Plural, useLingui } from "@lingui/react/macro";
import { type FocusEvent, type ReactNode, type SubmitEvent, useMemo, useState } from "react";
import { Autocomplete, Input, Label, ListBox, ListBoxItem, SearchField } from "react-aria-components";
import Button from "@/elements/Button.tsx";
import type { RegionCategory } from "../api/types";
import { getRegionLabels } from "../utils/region";
import { lowercaseFirst } from "../utils/text";

export type SearchListOption = {
   id: string;
   label: string;
   searchText?: string;
   content?: ReactNode;
   csbSlug?: string;
   sortName?: string;
   stationNumber?: number;
};

type Props = {
   regionCategory: RegionCategory;
   options: SearchListOption[];
   onSelect: (option: SearchListOption) => void;
   maxSuggestions?: number;
   children?: ReactNode;
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
   const [open, setOpen] = useState(false);

   const suggestions = useMemo(() => {
      const normalizedQuery = query.trim().toLowerCase();

      if (normalizedQuery.length === 0) {
         return [];
      }

      return options
         .filter((option) => {
            const searchable = `${option.label} ${option.searchText ?? ""}`.toLowerCase();

            return searchable.includes(normalizedQuery);
         })
         .slice(0, maxSuggestions);
   }, [maxSuggestions, options, query]);
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
            {/* Filtering happens above, so the collection gets no filter; Enter only picks what the user highlighted. */}
            <Autocomplete inputValue={query} onInputChange={handleChange} disableAutoFocusFirst>
               <SearchField className="contents">
                  <Label className="mb-1 basis-full font-bold">{label}</Label>
                  <div className="relative min-w-0 flex-1">
                     <Input
                        placeholder={placeholder}
                        className="w-full rounded-xs border border-blue-500 bg-white px-3 py-2.5 font-sans placeholder:text-gray-300 focus-visible:outline-blue-400 data-focused:outline-2 data-focused:outline-blue-400 sm:px-4 sm:py-3 [&::-webkit-search-cancel-button]:appearance-none"
                     />
                     {isOpen && (
                        <ListBox
                           aria-label={label}
                           items={suggestions}
                           className="absolute inset-x-0 top-full z-10 mt-1 max-h-75 divide-y divide-gray-200 overflow-y-auto rounded-xs border border-blue-500 bg-white"
                        >
                           {(option) => (
                              <ListBoxItem
                                 id={`${option.id}-${option.csbSlug ?? ""}`}
                                 textValue={option.label}
                                 onAction={() => selectOption(option)}
                                 className="flex min-h-12 cursor-pointer select-none items-center p-3 data-focused:bg-blue-50 data-hovered:bg-blue-50"
                              >
                                 {option.content ?? option.label}
                              </ListBoxItem>
                           )}
                        </ListBox>
                     )}
                  </div>
               </SearchField>
            </Autocomplete>
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
