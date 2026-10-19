import type { MessageDescriptor } from "@lingui/core";
import { msg } from "@lingui/core/macro";
import { Trans, useLingui } from "@lingui/react/macro";
import type { TimelineVariant } from "@/api/types.ts";
import { Timeline, type TimelineContextProps } from "@/components/Timeline/Timeline.tsx";
import TimelineEntry, { getTimelineDate, SBTimelineEntry } from "@/components/Timeline/TimelineEntry.tsx";

export const VARIANT_DESCRIPTIONS: Record<TimelineVariant, MessageDescriptor | null> = {
   CSO: msg`Het stembureau doet een sneltelling per partij. Het gemeentelijk stembureau telt de volgende dag alles nog een keer na en telt de stemmen per kandidaat op een centrale tellocatie. Die telresultaten staan in het verslag van het gemeentelijk stembureau/stembureau voor het openbaar lichaam.`,
   DSO: msg`Het stembureau doet een uitgebreide telling op het stembureau. Het gemeentelijk stembureau telt de volgende dag de uitkomsten bij elkaar op. Die telresultaten staan in het verslag van het gemeentelijk stembureau/stembureau voor het openbaar lichaam.`,
   DEFAULT: null,
};

type Props = TimelineContextProps;

export function SBTimeline({ variant = "DEFAULT", dates, documents }: Props) {
   const { t } = useLingui();

   const variantDescription = VARIANT_DESCRIPTIONS[variant];

   return (
      <div id="results-timeline">
         <h2 className="mb-4.5">
            <Trans>Hoe zijn de resultaten tot stand gekomen?</Trans>
         </h2>
         {variantDescription && <p className={"mb-4"}>{t(variantDescription)}</p>}
         <Timeline dates={dates} variant={variant} documents={documents}>
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
            <SBTimelineEntry />
         </Timeline>
      </div>
   );
}
