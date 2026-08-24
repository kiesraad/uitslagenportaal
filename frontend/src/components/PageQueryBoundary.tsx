import type { ReactNode } from "react";
import { ApiError } from "../api/client";
import { NotFoundPage } from "../pages/NotFoundPage";
import { Layout } from "./Layout";

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
   const labelLower = entityLabel.toLowerCase();

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
      return wrap(
         `${entityLabel} laden…`,
         `${entityLabel} laden…`,
         <div className="page-main">
            <div className="page-status" role="status" aria-live="polite">
               <p className="page-status-text">{entityLabel} laden…</p>
               <p>Een moment geduld, de gegevens worden opgehaald.</p>
            </div>
         </div>,
      );
   }

   if (errors?.some(isNotFoundError)) {
      return <NotFoundPage />;
   }

   if (isError) {
      return wrap(
         `${entityLabel} niet gevonden`,
         `Kan ${labelLower} niet laden.`,
         <div className="page-main">
            <div className="page-status" role="alert">
               <p className="page-status-text">Kan {labelLower} niet laden.</p>
               <button type="button" onClick={onRetry}>
                  Opnieuw proberen
               </button>
            </div>
         </div>,
      );
   }

   return null;
}
