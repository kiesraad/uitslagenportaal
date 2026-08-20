import { faArrowDown, faArrowUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import type { MessageDescriptor } from "@lingui/core";
import { msg } from "@lingui/core/macro";
import { Trans, useLingui } from "@lingui/react/macro";
import { useMemo, useState } from "react";
import type { TimelineVariant } from "@/api/types.ts";
import type { TimelineEntry } from "../Timeline";
import Timeline from "../Timeline";

type SortDirection = "desc" | "asc";

const VARIANT_DESCRIPTIONS: Record<TimelineVariant, MessageDescriptor | null> = /* @__PURE__ */ (() => ({
   CSO: msg`Het stembureau doet een sneltelling per partij. Het gemeentelijk stembureau telt de volgende dag alles nog een keer na en telt de stemmen per kandidaat op een centrale tellocatie. Die telresultaten staan in het verslag van het gemeentelijk stembureau/stembureau voor het openbaar lichaam.`,
   DSO: msg`Het stembureau doet een uitgebreide telling op het stembureau. Het gemeentelijk stembureau telt de volgende dag de uitkomsten bij elkaar op. Die telresultaten staan in het verslag van het gemeentelijk stembureau/stembureau voor het openbaar lichaam.`,
   DEFAULT: null,
}))();

type Props = {
   description?: string;
   variant?: TimelineVariant;
   entries: TimelineEntry[];
};
export default function ResultsTimeline({ description, variant, entries }: Props) {
   // 'desc' shows the most recent entry on top ("Laatste stap bovenaan").
   const [direction, setDirection] = useState<SortDirection>("desc");
   const { t } = useLingui();

   const variantDescription = variant ? VARIANT_DESCRIPTIONS[variant] : null;
   const resolvedDescription = description ?? (variantDescription ? t(variantDescription) : "");
   const sortedEntries = useMemo(() => {
      const factor = direction === "desc" ? -1 : 1;
      return [...entries].sort((a, b) => factor * (new Date(a.date).getTime() - new Date(b.date).getTime()));
   }, [entries, direction]);

   const toggleDirection = (event: React.MouseEvent<HTMLAnchorElement>) => {
      event.preventDefault();
      setDirection((current) => (current === "desc" ? "asc" : "desc"));
   };

   return (
      <div id="results-timeline">
         <h2 className="result-how-title">
            <Trans>Hoe zijn de resultaten tot stand gekomen?</Trans>
         </h2>
         {resolvedDescription ? <p className={"mb-4"}>{resolvedDescription}</p> : null}
         <p className="result-order-hint">
            <span>
               <FontAwesomeIcon icon={faArrowUp} color={direction === "desc" ? "Black" : "Grey"} />
               <FontAwesomeIcon icon={faArrowDown} color={direction === "asc" ? "Black" : "Grey"} />
            </span>
            <a href="#" onClick={toggleDirection}>
               {direction === "desc" ? t`Laatste stap bovenaan` : t`Eerste stap bovenaan`}
            </a>
         </p>

         {/* Timeline */}
         <Timeline entries={sortedEntries} />
      </div>
   );
}
