import { faCheck, faFile } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import ReactMarkdown from "react-markdown";
import { useFormatters } from "../utils/format";

export type TimelineEntryStatus = "pending" | "in-progress" | "done";
export interface TimelineEntry {
   status: TimelineEntryStatus;
   title: string;
   date: string;
   body: string;
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
export default function Timeline({ entries }: Props) {
   const { formatTimelineDate } = useFormatters();

   return (
      <div className="timeline">
         {entries.map((entry, i) => (
            <div key={entry.title} className={`timeline-item`}>
               <div
                  className={`timeline-line ${entry.status} ${entry.status === "done" ? "border-solid" : "border-dashed"} ${entries.length === i + 1 ? "last" : ""}`}
               ></div>
               <div className={"tl-marker-container"}>
                  <div className={`tl-marker ${entry.status}`}>
                     <div className={`${entry.status}-layer-1`}></div>
                     {entry.status === "done" ? <FontAwesomeIcon icon={faCheck} /> : null}
                  </div>
               </div>
               <div className="tl-body">
                  <div className="tl-title">{entry.title}</div>
                  <div className="tl-date">{formatTimelineDate(entry.date)}</div>
                  <div className="tl-desc">
                     <ReactMarkdown>{entry.body}</ReactMarkdown>
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
            </div>
         ))}
      </div>
   );
}
