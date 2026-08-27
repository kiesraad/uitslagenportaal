import { Trans, useLingui } from "@lingui/react/macro";
import { isRouteErrorResponse, useRouteError } from "react-router";
import { Layout } from "@/components/Layout.tsx";
import { isNotFoundError } from "@/components/PageQueryBoundary.tsx";
import PageTop from "@/components/PageTop.tsx";
import { ApiError } from "../api/client.ts";
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
   if (isNotFoundError(error)) {
      return <NotFoundPage />;
   }

   const { heading, detail } = describeError(error);
   const title = t`Fout`;
   const description = t`Er is een fout opgetreden`;

   return (
      <Layout title={title} description={description}>
         <div>
            <PageTop title={title} subtitle={description} />
         </div>
         <div className="page-main">
            <h1>{heading || <Trans>Er is een fout opgetreden</Trans>}</h1>
            {detail && <p>{detail}</p>}
         </div>
      </Layout>
   );
}
