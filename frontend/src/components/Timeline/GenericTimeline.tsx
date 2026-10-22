import { Trans, useLingui } from "@lingui/react/macro";
import { Timeline, type TimelineContextProps } from "@/components/Timeline/Timeline.tsx";
import TimelineEntry, {
   CsbCheckTimelineEntry,
   CsbResultPublishTimelineEntry,
   GSBVoteCountTimelineEntry,
   SBVoteCountTimelineEntry,
} from "@/components/Timeline/TimelineEntry.tsx";

type Props = Pick<TimelineContextProps, "dates">;

/**
 * The generic timeline shown on the homepage, the timeline tab (if there are multiple active elections) and
 * on each level when there are no results yet.
 */
export function GenericTimeline({ dates }: Props) {
   const { t } = useLingui();

   return (
      <div id="results-timeline">
         <Timeline dates={dates}>
            <CsbResultPublishTimelineEntry />
            <CsbCheckTimelineEntry />
            <TimelineEntry key="kieskring" event="electoral_district_vote_count" title={t`Optelling per kieskring`}>
               <p>
                  <Trans>
                     De kieskringen in Nederland tellen de resultaten van alle gemeenten in de kieskring bij elkaar op.
                  </Trans>
               </p>
            </TimelineEntry>
            <GSBVoteCountTimelineEntry />
            <SBVoteCountTimelineEntry />
         </Timeline>
      </div>
   );
}
