import { Plural, Trans } from "@lingui/react/macro";
import { type FocusEvent, type KeyboardEvent, type ReactNode, useCallback, useMemo, useRef, useState } from "react";
import {
   Autocomplete,
   Input,
   Label,
   ListBox,
   ListBoxItem,
   Popover,
   SearchField,
   useFilter,
} from "react-aria-components";

export type SearchListOption = {
   id: string;
   label: string;
   searchText?: string;
   content?: ReactNode;
   csbSlug?: string;
   sortName?: string;
   stationNumber?: number;
   sameLocationStationNumbers?: number[];
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

   return useMemo(() => {
      const suggestions = options.filter((option) => matches(option, query));
      const slicedSuggestions = suggestions.slice(0, maxSuggestions);
      return { suggestions: slicedSuggestions, total: suggestions.length };
   }, [maxSuggestions, options, query, matches]);
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
   const { suggestions, total } = useSuggestions(options, value, maxSuggestions);
   const isOpen = open && suggestions.length > 0;
   const shown = suggestions.length;
   const isTruncated = total > shown;
   const triggerRef = useRef<HTMLDivElement>(null);
   const popoverRef = useRef<HTMLElement>(null);

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
   // The popover is portalled out of this div, so its blur events bubble here but its elements aren't DOM children.
   function handleBlur(e: FocusEvent<HTMLDivElement>) {
      if (!e.currentTarget.contains(e.relatedTarget) && !popoverRef.current?.contains(e.relatedTarget)) {
         setOpen(false);
      }
   }

   return (
      <Autocomplete inputValue={value} onInputChange={handleChange} disableAutoFocusFirst>
         <SearchField className="contents">
            <Label className="mb-1 basis-full font-bold">{label}</Label>
            {/* biome-ignore lint/a11y/noStaticElementInteractions: onBlur only tracks focus leaving the controls inside. */}
            {/** biome-ignore lint/a11y/noNoninteractiveElementInteractions: onBlur only tracks focus leaving the controls inside */}
            <div ref={triggerRef} className="min-w-0 flex-1" onBlur={handleBlur}>
               <Input
                  placeholder={placeholder}
                  onKeyDown={handleKeyDown}
                  className="w-full rounded-xs border border-blue-500 bg-white px-3 py-2.5 font-sans placeholder:text-gray-300 focus-visible:outline-blue-400 data-focused:outline-2 data-focused:outline-blue-400 sm:px-4 sm:py-3 [&::-webkit-search-cancel-button]:appearance-none"
               />
               {/* Popover caps its height to the space left in the viewport, flipping above the input when that
                   side has more; non-modal so focus stays in the input. */}
               <Popover
                  ref={popoverRef}
                  triggerRef={triggerRef}
                  isOpen={isOpen}
                  isNonModal
                  placement="bottom start"
                  offset={4}
                  className="flex w-(--trigger-width) flex-col rounded-xs border border-blue-500 bg-white"
               >
                  <ListBox
                     aria-label={label}
                     className="max-h-100 min-h-0 flex-1 divide-y divide-gray-200 overflow-y-auto"
                  >
                     {suggestions.map((option) => {
                        const id = `${option.id}-${option.csbSlug ?? ""}`;
                        return (
                           <ListBoxItem
                              key={id}
                              id={id}
                              textValue={option.label}
                              onAction={() => handleSelect(option)}
                              className="flex min-h-12 cursor-pointer select-none items-center p-3 data-focused:bg-blue-50 data-hovered:bg-blue-50"
                           >
                              {option.content ?? option.label}
                           </ListBoxItem>
                        );
                     })}
                  </ListBox>
                  <p
                     aria-hidden="true"
                     onMouseDown={(e) => e.preventDefault()}
                     className="border-gray-200 border-t bg-gray-50 px-3 py-1 text-gray-700 text-sm"
                  >
                     <Trans>
                        {shown} van {total} resultaten
                     </Trans>
                  </p>
               </Popover>
            </div>
         </SearchField>
         {/* Rendered always, so screen readers pick up changes to its text. */}
         <div role="status" className="sr-only">
            {open &&
               value.trim().length > 0 &&
               (isTruncated ? (
                  <Trans>
                     {shown} van {total} resultaten
                  </Trans>
               ) : (
                  <Plural value={total} _0="Geen resultaten" one="# resultaat" other="# resultaten" />
               ))}
         </div>
      </Autocomplete>
   );
}
