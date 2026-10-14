import type { MessageDescriptor } from "@lingui/core";
import { msg } from "@lingui/core/macro";
import { Trans, useLingui } from "@lingui/react/macro";
import type { TimelineDate, TimelineVariant } from "@/api/types.ts";
import { Timeline } from "@/components/Timeline/Timeline.tsx";
import TimelineEntry, { getTimelineDate } from "@/components/Timeline/TimelineEntry.tsx";

export const VARIANT_DESCRIPTIONS: Record<TimelineVariant, MessageDescriptor | null> = (() => ({
   CSO: msg`Het stembureau doet een sneltelling per partij. Het gemeentelijk stembureau telt de volgende dag alles nog een keer na en telt de stemmen per kandidaat op een centrale tellocatie. Die telresultaten staan in het verslag van het gemeentelijk stembureau/stembureau voor het openbaar lichaam.`,
   DSO: msg`Het stembureau doet een uitgebreide telling op het stembureau. Het gemeentelijk stembureau telt de volgende dag de uitkomsten bij elkaar op. Die telresultaten staan in het verslag van het gemeentelijk stembureau/stembureau voor het openbaar lichaam.`,
   DEFAULT: null,
}))();

// The count in the stembureaus is the only step that differs per counting method.
const COUNT_BODIES: Record<TimelineVariant, MessageDescriptor> = (() => ({
   CSO: msg`Op de avond van de stemming tellen de stembureaus alleen de stemmen per lijst. Het GSB telt de volgende dag de stemmen per lijst en per kandidaat. Dit wordt ook wel 'centraal tellen' genoemd.`,
   DSO: msg`Op de avond van de stemming telt het stembureau de stemmen per lijst én per kandidaat. Het GSB controleert de volgende dag de processen-verbaal van de stembureaus. Bij (vermoedelijke) fouten worden de stemmen van dat stembureau geheel of gedeeltelijk opnieuw geteld.`,
   DEFAULT: msg`De stemmen worden geteld bij de stembureaus.`,
}))();

type Props = {
   variant?: TimelineVariant;
   dates: TimelineDate[];
};

export function SBTimeline({ variant = "DEFAULT", dates }: Props) {
   const { t } = useLingui();

   const variantDescription = VARIANT_DESCRIPTIONS[variant];

   return (
      <div id="results-timeline">
         <h2 className="mb-4.5">
            <Trans>Hoe zijn de resultaten tot stand gekomen?</Trans>
         </h2>
         {variantDescription && <p className={"mb-4"}>{t(variantDescription)}</p>}
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
                  {t(COUNT_BODIES[variant])}{" "}
                  <strong>
                     <Trans>Het is dus nog niet de officiële uitslag van de Kiesraad.</Trans>
                  </strong>
               </p>
            </TimelineEntry>
         </Timeline>
      </div>
   );
}
