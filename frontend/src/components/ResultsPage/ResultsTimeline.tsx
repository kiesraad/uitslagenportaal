import type { MessageDescriptor } from "@lingui/core";
import { msg } from "@lingui/core/macro";
import { useLingui } from "@lingui/react/macro";
import type { LocalizedText, TimelineEntry as TimelineEntryApiProps, TimelineVariant } from "@/api/types.ts";
import TimelineEntry from "@/components/Timeline/TimelineEntry.tsx";
import { resolveLocale } from "@/i18n";
import { Timeline } from "../Timeline/Timeline.tsx";

export const VARIANT_DESCRIPTIONS: Record<TimelineVariant, MessageDescriptor | null> = (() => ({
   CSO: msg`Het stembureau doet een sneltelling per partij. Het gemeentelijk stembureau telt de volgende dag alles nog een keer na en telt de stemmen per kandidaat op een centrale tellocatie. Die telresultaten staan in het verslag van het gemeentelijk stembureau/stembureau voor het openbaar lichaam.`,
   DSO: msg`Het stembureau doet een uitgebreide telling op het stembureau. Het gemeentelijk stembureau telt de volgende dag de uitkomsten bij elkaar op. Die telresultaten staan in het verslag van het gemeentelijk stembureau/stembureau voor het openbaar lichaam.`,
   DEFAULT: null,
}))();

type Props = {
   description?: string;
   variant?: TimelineVariant;
   entries: TimelineEntryApiProps[];
};
export default function ResultsTimeline({ description, variant, entries }: Props) {
   const { t } = useLingui();
   const { i18n } = useLingui();
   const locale = resolveLocale(i18n.locale);

   const variantDescription = variant ? VARIANT_DESCRIPTIONS[variant] : null;
   const resolvedDescription = description ?? (variantDescription ? t(variantDescription) : "");

   return (
      <Timeline description={resolvedDescription}>
         {entries.map((entry, i) => (
            <TimelineEntry
               // biome-ignore lint/suspicious/noArrayIndexKey: temp key
               key={i}
               {...entry}
               title={(entry.title as unknown as LocalizedText)?.[locale]}
            >
               {(entry.body as unknown as LocalizedText)?.[locale]}
            </TimelineEntry>
         ))}
      </Timeline>
   );
}
