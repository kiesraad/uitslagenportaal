import {Trans, useLingui} from "@lingui/react/macro";
import {Timeline, type TimelineContextProps, VARIANT_DESCRIPTIONS} from "@/components/Timeline/Timeline.tsx";
import {
   CsbCheckTimelineEntry,
   CsbResultPublishTimelineEntry,
   GSBVoteCountTimelineEntry,
   HSBVoteCountTimelineEntry,
   SBVoteCountTimelineEntry,
} from "@/components/Timeline/TimelineEntry.tsx";

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
