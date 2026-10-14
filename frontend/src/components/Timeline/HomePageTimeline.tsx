import { Trans, useLingui } from "@lingui/react/macro";
import type { TimelineDate } from "@/api/types.ts";
import { Timeline } from "@/components/Timeline/Timeline.tsx";
import TimelineEntry, { getTimelineDate } from "@/components/Timeline/TimelineEntry.tsx";

type Props = {
   dates: TimelineDate[];
};

export function HomePageTimeline({ dates }: Props) {
   const { t } = useLingui();

   return (
      <div id="results-timeline">
         <Timeline>
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
            <TimelineEntry
               key="count"
               date={getTimelineDate(dates, "sb_vote_count")}
               title={t`Telling in de stembureaus`}
            >
               <p>
                  <Trans>De stemmen worden geteld bij de stembureaus.</Trans>{" "}
                  <strong>
                     <Trans>Het is dus nog niet de officiële uitslag van de Kiesraad.</Trans>
                  </strong>
               </p>
            </TimelineEntry>
         </Timeline>
      </div>
   );
}
