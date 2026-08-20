import { useLingui } from "@lingui/react/macro";
import type { ReactNode } from "react";
import { Layout } from "./Layout";

type PageQueryBoundaryProps = {
   isLoading: boolean;
   isError: boolean;
   onRetry: () => void;
   /** Capitalised, standalone: "Gemeente". */
   entityLabel: string;
   /** The same noun mid-sentence: "gemeente". Falls back to `entityLabel`. */
   entityLabelInline?: string;
   withLayout?: boolean;
};

/**
 * Full-page loading / error gate for query-backed pages.
 * Use as an early return when `isLoading || isError`.
 */
export function PageQueryBoundary({
   isLoading,
   isError,
   onRetry,
   entityLabel,
   entityLabelInline,
   withLayout = true,
}: PageQueryBoundaryProps) {
   const { t } = useLingui();
   // Not `entityLabel.toLowerCase()`: which casing a noun takes mid-sentence is
   // a property of the language, so the caller passes the right form.
   const labelInline = entityLabelInline ?? entityLabel;

   const wrap = (title: string, description: string, children: ReactNode) =>
      withLayout ? (
         <Layout title={title} description={description}>
            <div className="page-top page-top-placeholder" aria-hidden="true" />
            {children}
         </Layout>
      ) : (
         children
      );

   if (isLoading) {
      const loading = t`${entityLabel} laden…`;
      return wrap(
         loading,
         loading,
         <div className="page-main">
            <div className="page-status" role="status" aria-live="polite">
               <p className="page-status-text">{loading}</p>
               <p>{t`Een moment geduld, de gegevens worden opgehaald.`}</p>
            </div>
         </div>,
      );
   }

   if (isError) {
      const cannotLoad = t`Kan ${labelInline} niet laden.`;
      return wrap(
         t`${entityLabel} niet gevonden`,
         cannotLoad,
         <div className="page-main">
            <div className="page-status" role="alert">
               <p className="page-status-text">{cannotLoad}</p>
               <button type="button" onClick={onRetry}>
                  {t`Opnieuw proberen`}
               </button>
            </div>
         </div>,
      );
   }

   return null;
}
