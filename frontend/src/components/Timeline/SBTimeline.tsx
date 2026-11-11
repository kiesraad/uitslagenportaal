import { Trans, useLingui } from "@lingui/react/macro";
import { Timeline, type TimelineContextProps, VARIANT_DESCRIPTIONS } from "@/components/Timeline/Timeline.tsx";
import TimelineEntry, {
   CorrectionTimelineEntry,
   CsbCheckTimelineEntry,
   CsbResultPublishTimelineEntry,
   GSBVoteCountTimelineEntry,
   HSBVoteCountTimelineEntry,
   MunicipalityRecountTimelineEntry,
   SBVoteCountTimelineEntry,
} from "@/components/Timeline/TimelineEntry.tsx";

type Props = TimelineContextProps;

export function SBTimeline({ variant = "DEFAULT", dates, ...timelineProps }: Props) {
   const { t } = useLingui();

   const variantDescription = VARIANT_DESCRIPTIONS[variant];
   // The candidate count is the gemeente's 510b.
   const countDate = timelineProps.municipality?.count_date;

   return (
      <div id="results-timeline">
         <h2 className="mb-4.5">
            <Trans>Hoe zijn de resultaten tot stand gekomen?</Trans>
         </h2>
         {variantDescription && <p className={"mb-4"}>{t(variantDescription)}</p>}
         <Timeline dates={dates} variant={variant} {...timelineProps}>
            <CsbResultPublishTimelineEntry />
            <MunicipalityRecountTimelineEntry />
            <CorrectionTimelineEntry />
            <CsbCheckTimelineEntry />
            <HSBVoteCountTimelineEntry />
            <GSBVoteCountTimelineEntry />
            {variant === "CSO" && (
               <TimelineEntry
                  title={t`Telling per lijst en kandidaat`}
                  event="municipality_vote_count"
                  doneAt={countDate}
                  document_types={["PDF_NA31-2-B1"]}
               >
                  <Trans>
                     Het gemeentelijk stembureau telt per stembureau alle stembiljetten op kandidaatsniveau: voor welke
                     kandidaten per partij de stemmen precies zijn uitgebracht.{" "}
                     <strong>Deze telling is de basis van de officiële uitslag.</strong>
                  </Trans>
               </TimelineEntry>
            )}
            <SBVoteCountTimelineEntry />
         </Timeline>
      </div>
   );
}
