import { PassThrough } from "node:stream";
import { createReadableStreamFromReadable } from "@react-router/node";
import { isbot } from "isbot";
import type { RenderToPipeableStreamOptions } from "react-dom/server";
import { renderToPipeableStream } from "react-dom/server";
import type { EntryContext } from "react-router";
import { ServerRouter } from "react-router";

export const streamTimeout = 5_000;

export default function handleRequest(
   request: Request,
   responseStatusCode: number,
   responseHeaders: Headers,
   routerContext: EntryContext,
) {
   // The page depends on the `lang` cookie, so a shared cache must not hand it to someone else.
   responseHeaders.set("Cache-Control", "no-cache");

   if (request.method.toUpperCase() === "HEAD") {
      return new Response(null, { status: responseStatusCode, headers: responseHeaders });
   }

   return new Promise((resolve, reject) => {
      let shellRendered = false;
      const userAgent = request.headers.get("user-agent");
      const readyOption: keyof RenderToPipeableStreamOptions =
         (userAgent && isbot(userAgent)) || routerContext.isSpaMode ? "onAllReady" : "onShellReady";

      let timeoutId: ReturnType<typeof setTimeout> | undefined = setTimeout(() => abort(), streamTimeout + 1000);

      const { pipe, abort } = renderToPipeableStream(<ServerRouter context={routerContext} url={request.url} />, {
         // The loaders have all data ready, so stream the page whole: otherwise React sends the root
         // Suspense fallback (the loading page) ahead of any page larger than about 12.8 KB.
         progressiveChunkSize: Number.POSITIVE_INFINITY,
         [readyOption]() {
            shellRendered = true;
            const body = new PassThrough({
               final(callback) {
                  clearTimeout(timeoutId);
                  timeoutId = undefined;
                  callback();
               },
            });

            responseHeaders.set("Content-Type", "text/html");
            pipe(body);
            resolve(
               new Response(createReadableStreamFromReadable(body), {
                  headers: responseHeaders,
                  status: responseStatusCode,
               }),
            );
         },
         onShellError(error: unknown) {
            reject(error);
         },
         onError(error: unknown) {
            responseStatusCode = 500;
            if (shellRendered) {
               console.error(error);
            }
         },
      });
   });
}
