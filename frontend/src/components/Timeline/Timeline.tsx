import { faCheck, faFile } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import type { MessageDescriptor } from "@lingui/core";
import { msg } from "@lingui/core/macro";
import { useLingui } from "@lingui/react";
import ReactMarkdown from "react-markdown";
import type { LocalizedText } from "@/api/types.ts";
import { resolveLocale } from "@/i18n";
import { useFormatters } from "@/utils/format.ts";

export type TimelineEntryStatus = "pending" | "in-progress" | "done";
export interface TimelineEntryProps {
   status: TimelineEntryStatus;
   title: LocalizedText;
   date: string;
   body: LocalizedText;
   link?: string;
   files?: {
      name: string;
      url: string;
      type: string;
      size: string;
      description: string;
   }[];
}
type TimelineProps = {
   entries: TimelineEntryProps[];
};

// The marker shows the status visually; this is the text screen readers get instead.
const STATUS_LABELS: Record<TimelineEntryStatus, MessageDescriptor> = (() => ({
   done: msg`afgerond`,
   "in-progress": msg`bezig`,
   pending: msg`nog niet gestart`,
}))();

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

export function Timeline({ entries }: TimelineProps) {
   return (
      <ol className="flex flex-col">
         {entries.map((entry, i) => (
            <TimelineEntry
               // biome-ignore lint/suspicious/noArrayIndexKey: temp key
               key={i}
               status={entry.status}
               title={entry.title}
               date={entry.date}
               body={entry.body}
               link={entry.link}
            />
         ))}
      </ol>
   );
}

export function TimelineEntry({ status, title, date, body, link, files }: TimelineEntryProps) {
   const { formatTimelineDate } = useFormatters();
   const { i18n } = useLingui();

   const locale = resolveLocale(i18n.locale);
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
               {title[locale]}
               <span className="sr-only">, {i18n._(STATUS_LABELS[status])}</span>
            </h3>
            <div className="mb-1.5 text-muted">{formatTimelineDate(date)}</div>
            <div className="flex flex-col gap-4.5 leading-6">
               <ReactMarkdown>{body[locale]}</ReactMarkdown>
            </div>
            {link && (
               <div className="mt-1.5">
                  <a href={link}>{link}</a>
               </div>
            )}
            {files ? (
               <div className="mt-3 flex flex-col gap-2 text-xs">
                  {files.map((file) => (
                     <a href={file.url} key={file.url} className="flex gap-2 bg-box-bg p-3 hover:no-underline">
                        <FontAwesomeIcon icon={faFile} />
                        <div className="flex flex-col">
                           <span className="mb-1 text-blue">
                              <span className="font-semibold">{file.name}</span> ({file.type}, {file.size})
                           </span>
                           <span className="text-muted">{file.description}</span>
                        </div>
                     </a>
                  ))}
               </div>
            ) : null}
         </div>
      </li>
   );
}
