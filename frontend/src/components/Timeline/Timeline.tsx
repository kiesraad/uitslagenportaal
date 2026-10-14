import { faArrowDown, faArrowUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans, useLingui } from "@lingui/react/macro";
import { type ReactElement, useMemo } from "react";
import type { TimelineEntryProps } from "@/components/Timeline/TimelineEntry.tsx";
import { usePersistedState } from "@/hooks/usePersistedState.ts";

const TIMELINE_ORDER_KEY = "timeline-order-desc";

type TimelineProps = {
   children: ReactElement<TimelineEntryProps>[];
   description?: string;
};

export function Timeline({ children }: TimelineProps) {
   const { t } = useLingui();
   const [sortDesc, setSortDesc] = usePersistedState<boolean>(
      TIMELINE_ORDER_KEY,
      true,
      (value) => typeof value === "boolean",
   );
   const factor = sortDesc ? -1 : 1;

   const sorted = useMemo(() => {
      return [...children].sort(
         (a, b) => factor * (new Date(a.props.date.date).getTime() - new Date(b.props.date.date).getTime()),
      );
   }, [children, factor]);

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
