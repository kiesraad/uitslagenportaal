import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faFolder } from "@fortawesome/free-regular-svg-icons";
import { faFile, faFilePdf, faFileZipper, faTable } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import type { MessageDescriptor } from "@lingui/core";
import { msg } from "@lingui/core/macro";
import { useLingui } from "@lingui/react/macro";
import type { ReactNode } from "react";
import type { ElectionDocument, PollingStationPvArchive } from "../../api/types";
import { useFormatters } from "../../utils/format";

type ReportFile = ElectionDocument & {
   icon: ReactNode;
};

type Props = {
   title: string;
   subtitle?: string;
   description: string;
   documents: ElectionDocument[] | undefined;
   pollingStationPvArchive?: PollingStationPvArchive | null;
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
   EML510c: {
      name: msg`EML_NL tellingbestand 510c`,
      fileType: "xml",
      icon: faFolder,
      description: msg`Output van de optelsoftware, bevat de optelling van het hoofdstembureau.`,
   },
   EML510d: {
      name: msg`EML_NL tellingbestand 510d`,
      fileType: "xml",
      icon: faFolder,
      description: msg`Output van de optelsoftware, bevat de resultaten van alle onderliggende regio's en de totaaltellingen.`,
   },
   "CSV_OSV4-3": {
      name: msg`OSV4-3 tellingbestand`,
      fileType: "csv",
      icon: faTable,
      description: msg`Output van de optelsoftware, bevat alle resultaten voor de regio en onderliggende regio's.`,
   },
   "PDF_N10-1": {
      name: msg`Proces-verbaal stembureau`,
      fileType: "pdf",
      icon: faFilePdf,
      description: msg`Het ondertekende proces-verbaal van het stembureau.`,
   },
   "PDF_N10-2": {
      name: msg`Proces-verbaal stembureau in een gemeente die CSB is`,
      fileType: "pdf",
      icon: faFilePdf,
      description: msg`Het ondertekende proces-verbaal van het stembureau in een gemeente die CSB is.`,
   },
   "PDF_NA14-1": {
      name: msg`Corrigendum proces-verbaal stembureau`,
      fileType: "pdf",
      icon: faFilePdf,
      description: msg`Corrigendum op het proces-verbaal van het stembureau.`,
   },
   "PDF_NA31-1": {
      name: msg`Proces-verbaal gemeentelijk stembureau (DSO)`,
      fileType: "pdf",
      icon: faFilePdf,
      description: msg`Het ondertekende proces-verbaal van het gemeentelijk stembureau bij decentrale stemopneming.`,
   },
   "PDF_NA31-2": {
      name: msg`Proces-verbaal gemeentelijk stembureau (CSO)`,
      fileType: "pdf",
      icon: faFilePdf,
      description: msg`Het ondertekende proces-verbaal van het gemeentelijk stembureau bij centrale stemopneming.`,
   },
   "PDF_NA14-2": {
      name: msg`Corrigendum proces-verbaal gemeentelijk stembureau`,
      fileType: "pdf",
      icon: faFilePdf,
      description: msg`Corrigendum op het proces-verbaal van het gemeentelijk stembureau.`,
   },
   PDF_O7: {
      name: msg`Proces-verbaal hoofdstembureau`,
      fileType: "pdf",
      icon: faFilePdf,
      description: msg`Het ondertekende proces-verbaal van het hoofdstembureau.`,
   },
   "PDF_P22-1": {
      name: msg`Proces-verbaal centraal stembureau met meerdere kieskringen`,
      fileType: "pdf",
      icon: faFilePdf,
      description: msg`Het ondertekende proces-verbaal van het centraal stembureau voor een verkiezing met meerdere kieskringen.`,
   },
   "PDF_P22-2": {
      name: msg`Proces-verbaal centraal stembureau met één kieskring`,
      fileType: "pdf",
      icon: faFilePdf,
      description: msg`Het ondertekende proces-verbaal van het centraal stembureau voor een verkiezing met één kieskring.`,
   },
}))();

function toReportFiles(documents: ElectionDocument[] | undefined): ReportFile[] {
   return (documents ?? []).map((document) => ({
      ...document,
      icon: <FontAwesomeIcon icon={FILE_TYPE_MAPPINGS[document.file_type]?.icon ?? faFile} />,
   }));
}

export default function ReportsWithResults({
   title,
   subtitle,
   description,
   documents,
   pollingStationPvArchive,
}: Props) {
   const { t } = useLingui();
   const { formatFileSize } = useFormatters();
   const files = toReportFiles(documents);
   const presentCount = pollingStationPvArchive?.present_count ?? 0;
   const totalCount = pollingStationPvArchive?.total_count ?? 0;

   /** The API sends the size as a string; anything unparseable is shown as-is. */
   function formatSize(size: number | string): string {
      const bytes = typeof size === "string" ? Number(size) : size;

      if (!Number.isFinite(bytes) || bytes < 0) {
         return String(size);
      }

      return formatFileSize(bytes);
   }

   if (files.length === 0 && !pollingStationPvArchive) {
      return null;
   }

   return (
      <div className={"results-reports"}>
         <h3 className={"results-reports-title mb-2"}>{title}</h3>
         {subtitle && <p className={"results-reports-subtitle mb-3"}>{subtitle}</p>}
         <p className={"results-reports-description mb-3"}>{description}</p>
         <div className={"results-reports-files"}>
            {files.map((file) => {
               const mapping = FILE_TYPE_MAPPINGS[file.file_type];
               // Corrections stack on one form, so each past the first names its place in the stack.
               const name = mapping ? t(mapping.name) : file.name;
               const title = file.correction_number > 1 ? `${name} ${file.correction_number}` : name;

               return (
                  <div key={file.url} className={"results-reports-item"}>
                     <div className={"results-reports-icon"}>{file.icon}</div>
                     <div className={"results-reports-content"}>
                        <a href={file.url} className={"results-reports-content-title"} download>
                           <span className="font-semibold">{title}</span> ({mapping?.fileType ?? file.type},{" "}
                           {formatSize(file.size)})
                        </a>
                        <span className="results-reports-description-text">
                           {mapping ? t(mapping.description) : file.description}
                        </span>
                     </div>
                  </div>
               );
            })}
            {pollingStationPvArchive && (
               <div className={"results-reports-item"}>
                  <div className={"results-reports-icon"}>
                     <FontAwesomeIcon icon={faFileZipper} />
                  </div>
                  <div className={"results-reports-content"}>
                     <a href={pollingStationPvArchive.url} className={"results-reports-content-title"} download>
                        <span className="font-semibold">{t`Processen-verbaal van alle stembureaus`}</span> (zip,{" "}
                        {formatSize(pollingStationPvArchive.size)})
                     </a>
                     <span className="results-reports-description-text">
                        {t`Handgeschreven verslagen van ${presentCount} van de ${totalCount} stembureaus`}
                     </span>
                  </div>
               </div>
            )}
         </div>
      </div>
   );
}
