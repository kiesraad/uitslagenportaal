import { Trans } from "@lingui/react/macro";
import { useId } from "react";
import type { ViewablePv } from "./ResultsPageColumns";

type Props = {
   pvs: ViewablePv[];
   selected: ViewablePv;
   onSelect: (url: string) => void;
};

/** Picks which of the region's PVs is shown; renders nothing when there is only one. */
export default function PvSelect({ pvs, selected, onSelect }: Props) {
   const id = useId();
   if (pvs.length < 2) return null;

   return (
      <div className="flex flex-col gap-1">
         <label htmlFor={id}>
            <Trans>Kies een proces-verbaal</Trans>
         </label>
         <select
            id={id}
            value={selected.url}
            onChange={(event) => onSelect(event.target.value)}
            className="rounded border border-gray-400 bg-white px-2 py-1"
         >
            {pvs.map((pv) => (
               <option key={pv.url} value={pv.url}>
                  {pv.label}
               </option>
            ))}
         </select>
      </div>
   );
}
