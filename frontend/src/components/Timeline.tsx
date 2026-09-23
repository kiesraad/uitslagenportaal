import { faCheck, faFile } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import type { MessageDescriptor } from "@lingui/core";
import { msg } from "@lingui/core/macro";
import { useLingui } from "@lingui/react";
import ReactMarkdown from "react-markdown";
import type { LocalizedText } from "../api/types";
import { resolveLocale } from "../i18n";
import { useFormatters } from "../utils/format";

export type TimelineEntryStatus = "pending" | "in-progress" | "done";
export interface TimelineEntry {
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
type Props = {
   entries: TimelineEntry[];
};

// The marker shows the status visually; this is the text screen readers get instead.
const STATUS_LABELS: Record<TimelineEntryStatus, MessageDescriptor> = (() => ({
   done: msg`afgerond`,
   "in-progress": msg`bezig`,
   pending: msg`nog niet gestart`,
}))();
export default function Timeline({ entries }: Props) {
   const { formatTimelineDate } = useFormatters();
   const { i18n } = useLingui();
   const locale = resolveLocale(i18n.locale);

   return (
      <ol className="timeline">
         {entries.map((entry, i) => (
            <li key={entry.title[locale]} className={`timeline-item`}>
               <div
                  aria-hidden="true"
                  className={`timeline-line ${entry.status} ${entry.status === "done" ? "border-solid" : "border-dashed"} ${entries.length === i + 1 ? "last" : ""}`}
               ></div>
               <div className={"tl-marker-container"} aria-hidden="true">
                  <div className={`tl-marker ${entry.status}`}>
                     <div className={`${entry.status}-layer-1`}></div>
                     {entry.status === "done" ? <FontAwesomeIcon icon={faCheck} /> : null}
                  </div>
               </div>
               <div className="tl-body">
                  <h3 className="tl-title">
                     {entry.title[locale]}
                     <span className="sr-only">, {i18n._(STATUS_LABELS[entry.status])}</span>
                  </h3>
                  <div className="tl-date">{formatTimelineDate(entry.date)}</div>
                  <div className="tl-desc">
                     <ReactMarkdown>{entry.body[locale]}</ReactMarkdown>
                  </div>
                  {entry.link && (
                     <div className="tl-link">
                        <a href={entry.link}>{entry.link}</a>
                     </div>
                  )}
                  {entry.files ? (
                     <div className="tl-files mt-3">
                        {entry.files.map((file) => (
                           <a href={file.url} key={file.url} className={"tl-files-item"}>
                              <FontAwesomeIcon icon={faFile} />
                              <div className={"tl-files-content"}>
                                 <span className={"tl-files-content-title mb-1"}>
                                    <span className="font-semibold">{file.name}</span> ({file.type}, {file.size})
                                 </span>
                                 <span className={"tl-files-content-desc"}>{file.description}</span>
                              </div>
                           </a>
                        ))}
                     </div>
                  ) : null}
               </div>
            </li>
         ))}
      </ol>
   );
}
