import { Plural } from "@lingui/react/macro";
import { type FocusEvent, type KeyboardEvent, type ReactNode, useCallback, useMemo, useState } from "react";
import { Autocomplete, Input, Label, ListBox, ListBoxItem, SearchField, useFilter } from "react-aria-components";

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
   label: string;
   placeholder: string;
   value: string;
   onChange: (value: string) => void;
   options: SearchListOption[];
   onSelect: (option: SearchListOption) => void;
   // Pass `isOpen` to control the listbox from outside; leave it out and the component opens and closes itself.
   isOpen?: boolean;
   onOpenChange?: (isOpen: boolean) => void;
   maxSuggestions?: number;
};

export function useOptionMatcher() {
   const { contains } = useFilter({ sensitivity: "base" });

   return useCallback(
      (option: SearchListOption, query: string) => {
         const normalizedQuery = query.trim();
         return normalizedQuery.length > 0 && contains(`${option.label} ${option.searchText ?? ""}`, normalizedQuery);
      },
      [contains],
   );
}

function useSuggestions(options: SearchListOption[], query: string, maxSuggestions: number) {
   const matches = useOptionMatcher();

   return useMemo(
      () => options.filter((option) => matches(option, query)).slice(0, maxSuggestions),
      [maxSuggestions, options, query, matches],
   );
}

export default function SearchAutocomplete({
   label,
   placeholder,
   value,
   onChange,
   options,
   onSelect,
   isOpen: isOpenProp,
   onOpenChange,
   maxSuggestions = 10,
}: Props) {
   const [internalOpen, setInternalOpen] = useState(false);
   const open = isOpenProp ?? internalOpen;
   const suggestions = useSuggestions(options, value, maxSuggestions);
   const isOpen = open && suggestions.length > 0;

   function setOpen(next: boolean) {
      if (isOpenProp === undefined) {
         setInternalOpen(next);
      }
      onOpenChange?.(next);
   }

   function handleChange(next: string) {
      setOpen(true);
      onChange(next);
   }

   function handleSelect(option: SearchListOption) {
      setOpen(false);
      onSelect(option);
   }

   // Enter without a highlighted suggestion submits the surrounding form; with one, `onAction` fires on keyup instead.
   // `SearchField`'s `onSubmit` can't tell the two apart: it fires in both cases.
   function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
      if (e.key === "Enter" && !e.currentTarget.hasAttribute("aria-activedescendant")) {
         setOpen(false);
      }
   }

   // Clicking a suggestion focuses the listbox, so only close once focus leaves the input and listbox altogether.
   function handleBlur(e: FocusEvent<HTMLDivElement>) {
      if (!e.currentTarget.contains(e.relatedTarget)) {
         setOpen(false);
      }
   }

   return (
      <Autocomplete inputValue={value} onInputChange={handleChange} disableAutoFocusFirst>
         <SearchField className="contents">
            <Label className="mb-1 basis-full font-bold">{label}</Label>
            {/* biome-ignore lint/a11y/noStaticElementInteractions: onBlur only tracks focus leaving the controls inside. */}
            {/** biome-ignore lint/a11y/noNoninteractiveElementInteractions: onBlur only tracks focus leaving the controls inside */}
            <div className="relative min-w-0 flex-1" onBlur={handleBlur}>
               <Input
                  placeholder={placeholder}
                  onKeyDown={handleKeyDown}
                  className="w-full rounded-xs border border-blue-500 bg-white px-3 py-2.5 font-sans placeholder:text-gray-300 focus-visible:outline-blue-400 data-focused:outline-2 data-focused:outline-blue-400 sm:px-4 sm:py-3 [&::-webkit-search-cancel-button]:appearance-none"
               />
               {isOpen && (
                  <ListBox
                     aria-label={label}
                     items={suggestions}
                     className="absolute inset-x-0 top-full z-10 mt-1 max-h-75 divide-y divide-gray-200 overflow-y-auto rounded-xs border border-blue-500 bg-white empty:invisible"
                  >
                     {(option) => (
                        <ListBoxItem
                           id={`${option.id}-${option.csbSlug ?? ""}`}
                           textValue={option.label}
                           onAction={() => handleSelect(option)}
                           className="flex min-h-12 cursor-pointer select-none items-center p-3 data-focused:bg-blue-50 data-hovered:bg-blue-50"
                        >
                           {option.content ?? option.label}
                        </ListBoxItem>
                     )}
                  </ListBox>
               )}
            </div>
         </SearchField>
         {/* Rendered always, so screen readers pick up changes to its text. */}
         <div role="status" className="sr-only">
            {open && value.trim().length > 0 && (
               <Plural value={suggestions.length} _0="Geen resultaten" one="# resultaat" other="# resultaten" />
            )}
         </div>
      </Autocomplete>
   );
}
