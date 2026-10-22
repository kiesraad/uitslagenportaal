import { faArrowDown, faArrowUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import type { MessageDescriptor } from "@lingui/core";
import { msg } from "@lingui/core/macro";
import { Trans, useLingui } from "@lingui/react/macro";
import { createContext, type ReactElement, useContext } from "react";
import type { ElectionDocument, Region, TimelineDate, TimelineVariant } from "@/api/types.ts";
import type { TimelineEntryProps } from "@/components/Timeline/TimelineEntry.tsx";
import { usePersistedState } from "@/hooks/usePersistedState.ts";

const TIMELINE_ORDER_KEY = "timeline-order-desc";

export const VARIANT_DESCRIPTIONS: Record<TimelineVariant, MessageDescriptor | null> = {
   CSO: msg`Het stembureau doet een sneltelling per partij. Het gemeentelijk stembureau telt de volgende dag alles nog een keer na en telt de stemmen per kandidaat op een centrale tellocatie. Die telresultaten staan in het verslag van het gemeentelijk stembureau/stembureau voor het openbaar lichaam.`,
   DSO: msg`Het stembureau doet een uitgebreide telling op het stembureau. Het gemeentelijk stembureau telt de volgende dag de uitkomsten bij elkaar op. Die telresultaten staan in het verslag van het gemeentelijk stembureau/stembureau voor het openbaar lichaam.`,
   DEFAULT: null,
};

export type TimelineContextProps = {
   variant?: TimelineVariant;
   dates: TimelineDate[];
   documents?: ElectionDocument[];
   region?: Region;
};

export const TimelineContext = createContext<TimelineContextProps>({
   variant: "DEFAULT",
   dates: [],
   documents: [],
});

export const useTimelineContext = () => useContext(TimelineContext);

type TimelineProps = TimelineContextProps & {
   children: (ReactElement<TimelineEntryProps> | boolean | null | undefined)[];
};

export function Timeline({ variant, dates, documents, region, children }: TimelineProps) {
   const { t } = useLingui();
   const [sortDesc, setSortDesc] = usePersistedState<boolean>(
      TIMELINE_ORDER_KEY,
      true,
      (value) => typeof value === "boolean",
   );

   return (
      <TimelineContext value={{ variant, dates, documents, region }}>
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
