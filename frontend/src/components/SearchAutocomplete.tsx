import { Autocomplete, Input, Label, ListBox, ListBoxItem, SearchField } from "react-aria-components";
import type { SearchListOption } from "./SearchBar";

type Props = {
   label: string;
   placeholder: string;
   value: string;
   onChange: (value: string) => void;
   options: SearchListOption[];
   isOpen: boolean;
   onSelect: (option: SearchListOption) => void;
};

export default function SearchAutocomplete({ label, placeholder, value, onChange, options, isOpen, onSelect }: Props) {
   return (
      <Autocomplete inputValue={value} onInputChange={onChange} disableAutoFocusFirst>
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
                     items={options}
                     className="absolute inset-x-0 top-full z-10 mt-1 max-h-75 divide-y divide-gray-200 overflow-y-auto rounded-xs border border-blue-500 bg-white empty:invisible"
                  >
                     {(option) => (
                        <ListBoxItem
                           id={`${option.id}-${option.csbSlug ?? ""}`}
                           textValue={option.label}
                           onAction={() => onSelect(option)}
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
   );
}
