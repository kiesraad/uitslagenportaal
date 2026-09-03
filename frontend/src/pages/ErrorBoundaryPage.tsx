import { faArrowRotateRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans, useLingui } from "@lingui/react/macro";
import { isRouteErrorResponse, useRouteError } from "react-router";
import { BaseLayout } from "@/components/BaseLayout.tsx";
import { LayoutMain } from "@/components/LayoutMain.tsx";
import Button from "@/elements/Button.tsx";
import { ApiError, isNotFoundError } from "../api/client.ts";
import { NotFoundPage } from "./NotFoundPage.tsx";

/** Reduces whatever was thrown to a heading and a body, whichever shape it has. */
function describeError(error: unknown): { heading: string; detail?: string } {
   if (isRouteErrorResponse(error)) {
      return { heading: `${error.status} ${error.statusText}`, detail: String(error.data ?? "") };
   }

   if (error instanceof ApiError) {
      return { heading: String(error.status), detail: error.message };
   }

   if (error instanceof Error) {
      return { heading: "", detail: error.message };
   }

   return { heading: "" };
}

export default function ErrorBoundaryPage() {
   const error = useRouteError();
   const { t } = useLingui();

   // A loader that 404s means the election, region or stembureau in the URL does not
   // exist, which is a not-found rather than a failure.
   // The ErrorBoundary replaces RootLayout, so the header and footer have to be added here.
   if (isNotFoundError(error)) {
      return (
         <BaseLayout>
            <NotFoundPage />
         </BaseLayout>
      );
   }

   const { heading, detail } = describeError(error);
   const title = t`Fout`;
   const description = t`Er is een fout opgetreden`;

   function reloadPage() {
      window.location.reload();
   }

   return (
      <BaseLayout>
         <LayoutMain title={title} description={description}>
            <div className="page-top flex-1 flex flex-col gap-3">
               <h1 className="text-3xl sm:text-4xl font-title font-bold whitespace-pre-line">{title}</h1>
               <p>{description}</p>
               <Button onClick={reloadPage} className="w-fit">
                  <FontAwesomeIcon icon={faArrowRotateRight} /> <Trans>Probeer opnieuw</Trans>
               </Button>
               <span>
                  <Trans>Details:</Trans>
               </span>
               <code className="text-xs whitespace-pre-line">
                  {heading} - {detail}
               </code>
            </div>
         </LayoutMain>
      </BaseLayout>
   );
}
