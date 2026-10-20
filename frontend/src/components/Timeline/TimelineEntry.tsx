import { faCheck } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import type { MessageDescriptor } from "@lingui/core";
import { msg, t } from "@lingui/core/macro";
import { Trans, useLingui } from "@lingui/react/macro";
import { type PropsWithChildren, type ReactNode, useContext, useMemo } from "react";
import type { ElectionDocumentFileType, TimelineDate, TimelineDateEvent, TimelineVariant } from "@/api/types.ts";
import ElectionFileEntry from "@/components/ElectionFileEntry.tsx";
import { TimelineContext } from "@/components/Timeline/Timeline.tsx";
import { electionDay, useFormatters } from "@/utils/format.ts";

// The marker shows the status visually; this is the text screen readers get instead.
const STATUS_LABELS: Record<TimelineEntryStatus, MessageDescriptor> = {
   done: msg`afgerond`,
   "in-progress": msg`bezig`,
   pending: msg`nog niet gestart`,
};

const STATUS_CLASSES: Record<TimelineEntryStatus, { line: string; marker: string; halo?: string }> = {
   done: {
      line: "border-solid border-done",
      marker: "-top-px -left-0.75 size-7 bg-done/34",
   },
   "in-progress": {
      line: "border-dashed border-done",
      marker: "top-2 left-1.5 size-2.25 bg-done",
      halo: "bg-done/41 outline-4 outline-done/22",
   },
   pending: {
      line: "border-dashed border-black/20",
      marker: "top-2 left-1.5 size-2.25 bg-muted",
      halo: "bg-muted opacity-10",
   },
};

/**
 * Get the TimelineDate object for the given event or default to now if it's not found.
 * @param dates
 * @param event
 */
export function getTimelineDate(dates: TimelineDate[], event: TimelineDateEvent) {
   return (
      dates.find((date) => date.event === event) ??
      ({
         date: new Date().toISOString(),
         event: event,
         qualifier: "all_day",
      } as TimelineDate)
   );
}

export type TimelineEntryStatus = "pending" | "in-progress" | "done";

export type TimelineEntryProps = {
   title: ReactNode;
   document_types?: ElectionDocumentFileType[];
} & (
   | {
        date?: TimelineDate;
        event: TimelineDateEvent;
     }
   | {
        date: TimelineDate;
        event?: undefined;
     }
);

export default function TimelineEntry({
   children,
   title,
   date,
   event,
   document_types = [],
}: PropsWithChildren<TimelineEntryProps>) {
   const { formatTimelineDate } = useFormatters();
   const { t } = useLingui();
   const { dates, documents } = useContext(TimelineContext);
   const resolved = event ? date || getTimelineDate(dates, event) : date;

   const status = useMemo((): TimelineEntryStatus => {
      const entryDate = new Date(resolved.date);
      if (Number.isNaN(entryDate.getTime())) {
         return "pending";
      }
      const today = electionDay(new Date());
      const entryDay = electionDay(entryDate);

      if (entryDay === today) {
         return "in-progress";
      }
      return entryDay < today ? "done" : "pending";
   }, [resolved.date]);

   const selectedDocs = useMemo(() => {
      return documents?.filter((doc) => document_types.includes(doc.file_type)) ?? [];
   }, [document_types, documents]);

   const classes = STATUS_CLASSES[status];

   return (
      <li className="group relative flex gap-7 pt-6 max-sm:gap-3.5">
         <div
            aria-hidden="true"
            className={`absolute top-5 left-2.5 -z-1 h-full border-l-2 group-last:hidden ${classes.line}`}
         ></div>
         <div
            className="relative -top-1 -z-1 h-9.25 w-5 min-w-5 bg-white max-sm:-top-2 max-lg:-top-1.75"
            aria-hidden="true"
         >
            <div
               className={`relative mt-1.5 flex shrink-0 items-center justify-center rounded-full text-muted ${classes.marker}`}
            >
               {classes.halo && <div className={`absolute -z-1 size-6 rounded-full ${classes.halo}`}></div>}
               {status === "done" ? <FontAwesomeIcon icon={faCheck} /> : null}
            </div>
         </div>
         <div className="min-w-0 flex-1 pb-6">
            <h3 className="mb-0.5 font-sans text-lg leading-normal">
               {title}
               <span className="sr-only">, {t(STATUS_LABELS[status])}</span>
            </h3>
            <div className="mb-1.5 text-muted">{formatTimelineDate(resolved)}</div>
            <div className="flex flex-col gap-4 leading-6">{children}</div>
            {selectedDocs.map((doc) => (
               <ElectionFileEntry key={doc.file_type} file={doc} className="mt-2 bg-info-bg p-3" />
            ))}
         </div>
      </li>
   );
}

const COUNT_BODIES: Record<TimelineVariant, MessageDescriptor> = {
   CSO: msg`Op de avond van de stemming tellen de stembureaus alleen de stemmen per lijst. Het GSB telt de volgende dag de stemmen per lijst en per kandidaat. Dit wordt ook wel 'centraal tellen' genoemd.`,
   DSO: msg`Op de avond van de stemming telt het stembureau de stemmen per lijst én per kandidaat. Het GSB controleert de volgende dag de processen-verbaal van de stembureaus. Bij (vermoedelijke) fouten worden de stemmen van dat stembureau geheel of gedeeltelijk opnieuw geteld.`,
   DEFAULT: msg`Na het sluiten van de stembussen tellen de leden van het stembureau hoeveel mensen hebben gestemd en hoeveel stemmen elke partij heeft gekregen. De voorlopige uitslag die je in het nieuws ziet is gebaseerd op de eerste tellingen van de stembureaus en wordt gepubliceerd door media en persbureaus.`,
};

export function SBTimelineEntry() {
   const { variant = "DEFAULT" } = useContext(TimelineContext);

   return (
      <TimelineEntry
         key="count"
         event="sb_vote_count"
         title={t`Telling in de stembureaus`}
         document_types={["EML510b"]}
      >
         <p>
            {t(COUNT_BODIES[variant])}{" "}
            <strong>
               <Trans>Het is dus nog niet de officiële uitslag van de Kiesraad.</Trans>
            </strong>
         </p>
      </TimelineEntry>
   );
}
