import type { MessageDescriptor } from "@lingui/core";
import { msg } from "@lingui/core/macro";
import { Trans, useLingui } from "@lingui/react/macro";
import type { TimelineVariant } from "@/api/types.ts";
import { Timeline, type TimelineContextProps } from "@/components/Timeline/Timeline.tsx";
import {
   CsbCheckTimelineEntry,
   CsbResultPublishTimelineEntry,
   GSBVoteCountTimelineEntry,
   HSBVoteCountTimelineEntry,
   SBVoteCountTimelineEntry,
} from "@/components/Timeline/TimelineEntry.tsx";

export const VARIANT_DESCRIPTIONS: Record<TimelineVariant, MessageDescriptor | null> = {
   CSO: msg`Het stembureau doet een sneltelling per partij. Het gemeentelijk stembureau telt de volgende dag alles nog een keer na en telt de stemmen per kandidaat op een centrale tellocatie. Die telresultaten staan in het verslag van het gemeentelijk stembureau/stembureau voor het openbaar lichaam.`,
   DSO: msg`Het stembureau doet een uitgebreide telling op het stembureau. Het gemeentelijk stembureau telt de volgende dag de uitkomsten bij elkaar op. Die telresultaten staan in het verslag van het gemeentelijk stembureau/stembureau voor het openbaar lichaam.`,
   DEFAULT: null,
};

type Props = TimelineContextProps;

export function GSBTimeline({ variant = "DEFAULT", dates, ...timelineProps }: Props) {
   const { t } = useLingui();

   const variantDescription = VARIANT_DESCRIPTIONS[variant];

   return (
      <div id="results-timeline">
         <h2 className="mb-4.5">
            <Trans>Hoe zijn de resultaten tot stand gekomen?</Trans>
         </h2>
         {variantDescription && <p className={"mb-4"}>{t(variantDescription)}</p>}
         <Timeline variant={variant} dates={dates} {...timelineProps}>
            <CsbResultPublishTimelineEntry />
            <CsbCheckTimelineEntry />
            <HSBVoteCountTimelineEntry />
            <GSBVoteCountTimelineEntry />
            <SBVoteCountTimelineEntry />
         </Timeline>
      </div>
   );
}
