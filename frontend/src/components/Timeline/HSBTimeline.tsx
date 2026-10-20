import { Trans, useLingui } from "@lingui/react/macro";
import { Timeline, type TimelineContextProps } from "@/components/Timeline/Timeline.tsx";
import TimelineEntry, { getTimelineDate, SBVoteCountTimelineEntry } from "@/components/Timeline/TimelineEntry.tsx";

type Props = Omit<TimelineContextProps, "variant">;

export function HSBTimeline({ dates, documents }: Props) {
   const { t } = useLingui();

   return (
      <div id="results-timeline">
         <h2 className="mb-4.5">
            <Trans>Hoe zijn de resultaten tot stand gekomen?</Trans>
         </h2>
         <Timeline dates={dates} documents={documents}>
            <TimelineEntry
               key="publication"
               date={getTimelineDate(dates, "csb_result_publish")}
               title={t`De Kiesraad publiceert de uitslag`}
            >
               <p>
                  <Trans>
                     In de uitslag staat hoeveel stemmen elke kandidaat heeft gekregen, hoeveel zetels elke partij
                     krijgt en welke mensen in de Tweede Kamer komen.
                  </Trans>
               </p>
            </TimelineEntry>
            <TimelineEntry
               key="check"
               date={getTimelineDate(dates, "csb_check")}
               title={t`Centraal Stembureau controleert`}
            >
               <p>
                  <Trans>
                     De Kiesraad controleert de telresultaten van alle kieskringen, gemeenten en stembureaus. Zijn alle
                     documenten compleet? Zijn alle stemmen meegeteld? Zijn er meldingen van kiezers die onderzocht
                     moeten worden? Als het nodig is, worden de resultaten van bepaalde stembureaus opnieuw geteld om
                     fouten te herstellen.
                  </Trans>
               </p>
               <p>
                  <Trans>
                     Pas als alles klopt worden de resultaten van alle kieskringen bij elkaar opgeteld tot de landelijke
                     uitslag.
                  </Trans>
               </p>
            </TimelineEntry>
            <TimelineEntry
               key="kieskring"
               date={getTimelineDate(dates, "electoral_district_vote_count")}
               title={t`Optelling per kieskring`}
            >
               <p>
                  <Trans>
                     De 20 kieskringen in Nederland tellen de resultaten van alle gemeenten in de kieskring bij elkaar
                     op.
                  </Trans>
               </p>
            </TimelineEntry>
            <TimelineEntry
               key="municipality"
               date={getTimelineDate(dates, "municipality_vote_count")}
               title={t`Optelling per gemeente`}
            >
               <p>
                  <Trans>
                     De resultaten van alle stembureaus worden gecontroleerd en van papier overgetypt in de
                     uitslagensoftware en opgeteld. Het gemeentelijk stembureau maakt een verslag en deelt de
                     telresultaten zodat ze kunnen worden meegenomen in de landelijke uitslag.
                  </Trans>
               </p>
            </TimelineEntry>
            <SBVoteCountTimelineEntry />
         </Timeline>
      </div>
   );
}
