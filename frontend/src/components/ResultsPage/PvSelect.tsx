import { faChevronDown } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans } from "@lingui/react/macro";
import { Button, Label, ListBox, ListBoxItem, Popover, Select, SelectValue } from "react-aria-components";
import type { ViewablePv } from "./ResultsPageColumns";

type Props = {
   pvs: ViewablePv[];
   selected: ViewablePv;
   onSelect: (url: string) => void;
};

/** Picks which of the region's PVs is shown; renders nothing when there is only one. */
export default function PvSelect({ pvs, selected, onSelect }: Props) {
   if (pvs.length < 2) return null;

   return (
      <Select value={selected.url} onChange={(url) => onSelect(String(url))} className="flex flex-col gap-1">
         <Label>
            <Trans>Kies een proces-verbaal</Trans>
         </Label>
         <Button className="flex cursor-pointer items-center justify-between gap-2 rounded-xs border border-blue-500 bg-white px-3 py-2 text-left data-focus-visible:outline-2 data-focus-visible:outline-blue-400">
            <SelectValue />
            <FontAwesomeIcon icon={faChevronDown} aria-hidden="true" />
         </Button>
         <Popover
            placement="bottom start"
            offset={4}
            className="w-(--trigger-width) rounded-xs border border-blue-500 bg-white"
         >
            <ListBox className="max-h-100 divide-y divide-gray-200 overflow-y-auto">
               {pvs.map((pv) => (
                  <ListBoxItem
                     key={pv.url}
                     id={pv.url}
                     textValue={pv.label}
                     className="flex min-h-12 cursor-pointer items-center p-3 select-none data-focused:bg-blue-50 data-hovered:bg-blue-50 data-selected:font-bold"
                  >
                     {pv.label}
                  </ListBoxItem>
               ))}
            </ListBox>
         </Popover>
      </Select>
   );
}
