import { useLingui } from "@lingui/react/macro";
import { createContext, type ReactNode, useContext, useMemo, useState } from "react";
import type { CertifiedDocument, TocEntry } from "@/api/types.ts";
import { FILE_TYPE_MAPPINGS } from "../ElectionFileEntry";
import ResultsSourceBox from "./ResultsSourceBox";

/** A proces-verbaal the viewer can show: one with both the PDF and its preview. */
export type ViewablePv = {
   url: string;
   previewUrl: string;
   toc: TocEntry[] | null;
   label: string;
};

type PvTarget = { pv: ViewablePv; page: number };

type PvViewerContextProps = {
   // Where a link to `content` goes: the selected PV when it has that page, else the first PV that has it.
   findTarget: (content: TocEntry["content"], listNumber?: number) => PvTarget | undefined;
   openViewerAt: (target: PvTarget) => void;
};

const PvViewerContext = createContext<PvViewerContextProps>({ findTarget: () => undefined, openViewerAt: () => {} });

export const usePvViewerContext = () => useContext(PvViewerContext);

function pageOf(pv: ViewablePv, content: TocEntry["content"], listNumber?: number) {
   return pv.toc?.find(
      (entry) => entry.content === content && (listNumber === undefined || entry.list_number === listNumber),
   )?.page;
}

type Props = {
   children: ReactNode;
   // Every proces-verbaal of the region, best first.
   documents?: CertifiedDocument[] | null;
   pvMayDiffer?: boolean;
};

export default function ResultsPageColumns({ children, documents, pvMayDiffer }: Props) {
   const { t, i18n } = useLingui();

   const pvs = useMemo<ViewablePv[]>(() => {
      const viewable = (documents ?? []).filter((document) => document.url && document.preview_url);
      // Several originals, as a stembureau's PV and its bijlage, are told apart by their form name.
      const originals = viewable.filter((document) => document.correction_number === null).length;
      return viewable.map((document) => ({
         url: document.url as string,
         previewUrl: document.preview_url as string,
         toc: document.toc,
         label:
            document.correction_number !== null
               ? t`Corrigendum ${document.correction_number}`
               : originals > 1 && FILE_TYPE_MAPPINGS[document.file_type]
                 ? i18n._(FILE_TYPE_MAPPINGS[document.file_type].name)
                 : t`Proces-verbaal`,
      }));
   }, [documents, t, i18n]);

   const [selectedUrl, setSelectedUrl] = useState<string | null>(null);
   // A PV of another region, as after navigating, falls back to the best one.
   const selected = pvs.find((pv) => pv.url === selectedUrl) ?? pvs[0];

   // The PV and page the viewer shows, or null while it is closed.
   const [viewer, setViewer] = useState<{ url: string; page: number } | null>(null);
   // Another PV, as after choosing one or going to another region, starts at page 1.
   const viewerPage = viewer && selected ? (viewer.url === selected.url ? viewer.page : 1) : null;

   // The PV that was open when a link switched to another one, as that one lacked the page.
   const [switchedFrom, setSwitchedFrom] = useState<{ to: string; from: string } | null>(null);
   const switchedFromLabel = switchedFrom && switchedFrom.to === selected?.url ? switchedFrom.from : null;

   function setViewerPage(page: number | null) {
      if (page === null) setSwitchedFrom(null);
      setViewer(page === null || !selected ? null : { url: selected.url, page });
   }

   function selectPv(url: string) {
      setSelectedUrl(url);
      setSwitchedFrom(null);
      if (viewer) setViewer({ url, page: 1 });
   }

   function findTarget(content: TocEntry["content"], listNumber?: number): PvTarget | undefined {
      for (const pv of selected ? [selected, ...pvs] : pvs) {
         const page = pageOf(pv, content, listNumber);
         if (page !== undefined) return { pv, page };
      }
      return undefined;
   }

   function openViewerAt({ pv, page }: PvTarget) {
      setSwitchedFrom(selected && pv.url !== selected.url ? { to: pv.url, from: selected.label } : null);
      setSelectedUrl(pv.url);
      setViewer({ url: pv.url, page });
   }

   return (
      <PvViewerContext value={{ findTarget, openViewerAt }}>
         <div className="page-main page-main-two-columns">
            <div className="flex flex-col gap-4 sm:gap-12">{children}</div>
            <div className="counting-results-column">
               <ResultsSourceBox
                  pvs={pvs}
                  selected={selected}
                  onSelect={selectPv}
                  pvMayDiffer={pvMayDiffer}
                  switchedFromLabel={switchedFromLabel}
                  viewerPage={viewerPage}
                  onViewerPageChange={setViewerPage}
               />
            </div>
         </div>
      </PvViewerContext>
   );
}
