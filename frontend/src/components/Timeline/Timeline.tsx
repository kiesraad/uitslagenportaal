import { faArrowDown, faArrowUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans, useLingui } from "@lingui/react/macro";
import { createContext, type ReactElement } from "react";
import type { ElectionDocument, TimelineDate, TimelineVariant } from "@/api/types.ts";
import type { TimelineEntryProps } from "@/components/Timeline/TimelineEntry.tsx";
import { usePersistedState } from "@/hooks/usePersistedState.ts";

const TIMELINE_ORDER_KEY = "timeline-order-desc";

export type TimelineContextProps = {
   variant?: TimelineVariant;
   dates: TimelineDate[];
   documents?: ElectionDocument[];
};

export const TimelineContext = createContext<TimelineContextProps>({
   variant: "DEFAULT",
   dates: [],
   documents: [],
});

type TimelineProps = {
   variant?: TimelineVariant;
   dates: TimelineDate[];
   documents?: ElectionDocument[];
   children: ReactElement<TimelineEntryProps>[];
};

export function Timeline({ variant, dates, documents, children }: TimelineProps) {
   const { t } = useLingui();
   const [sortDesc, setSortDesc] = usePersistedState<boolean>(
      TIMELINE_ORDER_KEY,
      true,
      (value) => typeof value === "boolean",
   );

   return (
      <TimelineContext value={{ variant, dates, documents }}>
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
         <ol className="flex flex-col">{sortDesc ? children : [...children].reverse()}</ol>
      </TimelineContext>
   );
}
