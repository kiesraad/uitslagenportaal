import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faFolder } from "@fortawesome/free-regular-svg-icons";
import { faFile } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import type { MessageDescriptor } from "@lingui/core";
import { msg } from "@lingui/core/macro";
import { useLingui } from "@lingui/react/macro";
import type { ReactNode } from "react";
import type { ElectionDocument } from "../../api/types";
import { useFormatters } from "../../utils/format";

type ReportFile = ElectionDocument & {
   icon: ReactNode;
};

type Props = {
   title: string;
   subtitle?: string;
   description: string;
   documents: ElectionDocument[] | undefined;
};

const FILE_TYPE_MAPPINGS: Record<
   string,
   { name: MessageDescriptor; fileType: string; description: MessageDescriptor; icon: IconDefinition }
> = (() => ({
   EML510b: {
      name: msg`EML_NL tellingbestand 510b`,
      fileType: "xml",
      icon: faFolder,
      description: msg`Output van de optelsoftware, bevat de resultaten van alle stembureaus en de optelling van de hele gemeente.`,
   },
}))();

function toReportFiles(documents: ElectionDocument[] | undefined): ReportFile[] {
   return (documents ?? []).map((document) => ({
      ...document,
      icon: <FontAwesomeIcon icon={FILE_TYPE_MAPPINGS[document.file_type]?.icon ?? faFile} />,
   }));
}

export default function ReportsWithResults({ title, subtitle, description, documents }: Props) {
   const { t } = useLingui();
   const { formatFileSize } = useFormatters();
   const files = toReportFiles(documents);

   /** The API sends the size as a string; anything unparseable is shown as-is. */
   function formatSize(size: number | string): string {
      const bytes = typeof size === "string" ? Number(size) : size;

      if (!Number.isFinite(bytes) || bytes < 0) {
         return String(size);
      }

      return formatFileSize(bytes);
   }

   if (files.length === 0) {
      return null;
   }

   return (
      <div className={"results-reports"}>
         <h3 className={"results-reports-title mb-2"}>{title}</h3>
         {subtitle && <h5 className={"results-reports-subtitle mb-3"}>{subtitle}</h5>}
         <p className={"results-reports-description mb-3"}>{description}</p>
         <div className={"results-reports-files"}>
            {files.map((file) => {
               const mapping = FILE_TYPE_MAPPINGS[file.file_type];

               return (
                  <div key={file.file_type} className={"results-reports-item"}>
                     <div className={"results-reports-icon"}>{file.icon}</div>
                     <div className={"results-reports-content"}>
                        <a href={file.url} className={"results-reports-content-title"} download>
                           <span className="font-semibold">{mapping ? t(mapping.name) : file.name}</span> (
                           {mapping?.fileType ?? file.type}, {formatSize(file.size)})
                        </a>
                        <span className="results-reports-description-text">
                           {mapping ? t(mapping.description) : file.description}
                        </span>
                     </div>
                  </div>
               );
            })}
         </div>
      </div>
   );
}
