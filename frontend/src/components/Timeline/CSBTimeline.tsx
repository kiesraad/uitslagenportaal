import { Trans } from "@lingui/react/macro";
import { Timeline, type TimelineContextProps } from "@/components/Timeline/Timeline.tsx";
import {
   CsbCheckTimelineEntry,
   CsbResultPublishTimelineEntry,
   GSBVoteCountTimelineEntry,
   HSBVoteCountTimelineEntry,
   SBVoteCountTimelineEntry,
} from "@/components/Timeline/TimelineEntry.tsx";

type Props = Omit<TimelineContextProps, "variant">;

export function CSBTimeline({ dates, ...timelineProps }: Props) {
   return (
      <div id="results-timeline">
         <h2 className="mb-4.5">
            <Trans>Hoe zijn de resultaten tot stand gekomen?</Trans>
         </h2>
         <Timeline dates={dates} {...timelineProps}>
            <CsbResultPublishTimelineEntry />
            <CsbCheckTimelineEntry />
            <HSBVoteCountTimelineEntry />
            <GSBVoteCountTimelineEntry />
            <SBVoteCountTimelineEntry />
         </Timeline>
      </div>
   );
}
