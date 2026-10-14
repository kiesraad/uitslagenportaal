import { faCheck, faFile } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import type { MessageDescriptor } from "@lingui/core";
import { msg } from "@lingui/core/macro";
import { useLingui } from "@lingui/react/macro";
import { type PropsWithChildren, type ReactNode, useMemo } from "react";
import type { TimelineDate, TimelineDateEvent } from "@/api/types.ts";
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

export interface TimelineEntryProps {
   title: ReactNode;
   date: TimelineDate;
}

export default function TimelineEntry({ children, title, date }: PropsWithChildren<TimelineEntryProps>) {
   const { formatTimelineDate } = useFormatters();
   const { t } = useLingui();

   const status = useMemo((): TimelineEntryStatus => {
      // If no date is given, we fall back to today
      const entryDate = new Date(date.date);
      if (Number.isNaN(entryDate.getTime())) {
         return "pending";
      }
      const today = electionDay(new Date());
      const entryDay = electionDay(entryDate);

      if (entryDay === today) {
         return "in-progress";
      }
      return entryDay < today ? "done" : "pending";
   }, [date]);

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
            <h3 className="mb-0.5 font-sans leading-normal">
               {title}
               <span className="sr-only">, {t(STATUS_LABELS[status])}</span>
            </h3>
            <div className="mb-1.5 text-muted">{formatTimelineDate(date)}</div>
            <div className="flex flex-col gap-4 leading-6">{children}</div>
         </div>
      </li>
   );
}

export interface TimelineFileProps {
   file: {
      name: string;
      url: string;
      type: string;
      size: string;
      description: string;
   };
}

export function TimelineFile({ file }: TimelineFileProps) {
   return (
      <a href={file.url} key={file.url} className="flex gap-2 bg-box-bg p-3 text-xs hover:no-underline">
         <FontAwesomeIcon icon={faFile} />
         <div className="flex flex-col">
            <span className="mb-1 text-blue">
               <span className="font-semibold">{file.name}</span> ({file.type}, {file.size})
            </span>
            <span className="text-muted">{file.description}</span>
         </div>
      </a>
   );
}
