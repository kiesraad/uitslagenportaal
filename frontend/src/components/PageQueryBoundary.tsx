import { useLingui } from "@lingui/react/macro";
import type { ReactNode } from "react";
import { ApiError } from "../api/client";
import { NotFoundPage } from "../pages/NotFoundPage";
import { lowercaseFirst } from "../utils/text";
import { LayoutMain } from "./LayoutMain.tsx";

type PageQueryBoundaryProps = {
   isLoading: boolean;
   isError: boolean;
   onRetry: () => void;
   entityLabel: string;
   withLayout?: boolean;
   errors?: unknown[];
};

export function isNotFoundError(error: unknown): boolean {
   return error instanceof ApiError && error.status === 404;
}

/**
 * Full-page loading / error gate for query-backed pages.
 * Use as an early return when `isLoading || isError`.
 */
export function PageQueryBoundary({
   isLoading,
   isError,
   onRetry,
   entityLabel,
   withLayout = true,
   errors,
}: PageQueryBoundaryProps) {
   const { t } = useLingui();
   const labelInline = lowercaseFirst(entityLabel);

   const wrap = (title: string, description: string, children: ReactNode) =>
      withLayout ? (
         <LayoutMain title={title} description={description}>
            <div className="page-top page-top-placeholder" aria-hidden="true" />
            {children}
         </LayoutMain>
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

   if (errors?.some(isNotFoundError)) {
      return <NotFoundPage />;
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
