import { faArrowDown, faArrowUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans, useLingui } from "@lingui/react/macro";
import type { ReactElement } from "react";
import type { TimelineEntryProps } from "@/components/Timeline/TimelineEntry.tsx";
import { usePersistedState } from "@/hooks/usePersistedState.ts";

const TIMELINE_ORDER_KEY = "timeline-order-desc";

type TimelineProps = {
   children: ReactElement<TimelineEntryProps>[];
};

// An unparseable date counts as the latest step, as TimelineEntry shows it as pending.
function entryTime(entry: ReactElement<TimelineEntryProps>): number {
   const time = new Date(entry.props.date.date).getTime();
   return Number.isNaN(time) ? Number.POSITIVE_INFINITY : time;
}

export function Timeline({ children }: TimelineProps) {
   const { t } = useLingui();
   const [sortDesc, setSortDesc] = usePersistedState<boolean>(
      TIMELINE_ORDER_KEY,
      true,
      (value) => typeof value === "boolean",
   );
   const factor = sortDesc ? -1 : 1;

   const sorted = [...children].sort((a, b) => {
      const timeA = entryTime(a);
      const timeB = entryTime(b);
      return timeA === timeB ? 0 : factor * (timeA < timeB ? -1 : 1);
   });

   return (
      <>
         <button type="button" onClick={() => setSortDesc((prev) => !prev)} className="result-order-hint">
            <span>
               <FontAwesomeIcon icon={faArrowUp} color={sortDesc ? "Black" : "Grey"} />
               <FontAwesomeIcon icon={faArrowDown} color={!sortDesc ? "Black" : "Grey"} />
            </span>
            <span className="text-blue-500">
               {/* The visible text is the current order; this says what pressing the button does. */}
               <span className="sr-only">
                  <Trans>Volgorde omdraaien, nu:</Trans>{" "}
               </span>
               {sortDesc ? t`Laatste stap bovenaan` : t`Eerste stap bovenaan`}
            </span>
         </button>
         <ol className="flex flex-col">{sorted}</ol>
      </>
   );
}
