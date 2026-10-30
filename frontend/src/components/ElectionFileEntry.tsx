import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faFolder } from "@fortawesome/free-regular-svg-icons";
import { faFile, faFilePdf, faFileZipper, faTable } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import type { MessageDescriptor } from "@lingui/core";
import { msg } from "@lingui/core/macro";
import { useLingui } from "@lingui/react";
import { useCallback, useMemo } from "react";
import { twMerge } from "tailwind-merge";
import type { ElectionDocument } from "@/api/types.ts";
import { useFormatters } from "@/utils/format.ts";

const FILE_TYPE_MAPPINGS: Record<
   string,
   { name: MessageDescriptor; fileType: string; description: MessageDescriptor; icon: IconDefinition }
> = {
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
   EML520: {
      name: msg`EML_NL resultaatbestand 520`,
      fileType: "xml",
      icon: faFolder,
      description: msg`Officieel resultaat van het centraal stembureau, met de zetelverdeling en de gekozen kandidaten.`,
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
   "PDF_P1F-1": {
      name: msg`Corrigendum proces-verbaal hoofdstembureau`,
      fileType: "pdf",
      icon: faFilePdf,
      description: msg`Corrigendum op het proces-verbaal van het hoofdstembureau.`,
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
   "PDF_SB-ZIP": {
      name: msg`Processen-verbaal van alle stembureaus`,
      fileType: "zip",
      icon: faFileZipper,
      description: msg`Handgeschreven verslagen van {present} van de {total} stembureaus`,
   },
};

type FileEntryProps = {
   file: ElectionDocument;
   className?: string;
};

export default function ElectionFileEntry({ file, className }: FileEntryProps) {
   const { i18n } = useLingui();
   const { formatFileSize } = useFormatters();
   const mapping = FILE_TYPE_MAPPINGS[file.file_type];

   // Corrections stack on one form, so each past the first names its place in the stack.
   const title = useMemo(() => {
      const name = mapping ? i18n._(mapping.name) : file.name;
      return file.correction_number > 1 ? `${name} ${file.correction_number}` : name;
   }, [file.correction_number, file.name, i18n, mapping]);

   const formatSize = useCallback(
      (size: number | string): string => {
         const bytes = typeof size === "string" ? Number(size) : size;

         if (!Number.isFinite(bytes) || bytes < 0) {
            return String(size);
         }

         return formatFileSize(bytes);
      },
      [formatFileSize],
   );

   return (
      <div key={file.url} className={twMerge("not-last:mb-2 flex", className)}>
         <div className="size-8 shrink-0 text-blue">
            <FontAwesomeIcon icon={mapping?.icon ?? faFile} />
         </div>
         <div className="flex flex-col">
            <a href={file.url} className="text-blue no-underline hover:underline" download>
               <span className="font-semibold">{title}</span> ({mapping?.fileType ?? file.type}, {formatSize(file.size)}
               )
            </a>
            <span>{mapping ? i18n._({ ...mapping.description, values: file.metadata }) : file.description}</span>
         </div>
      </div>
   );
}
