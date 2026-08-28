import { i18n } from "@lingui/core";
import { I18nProvider } from "@lingui/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type RenderOptions, render } from "@testing-library/react";
import { type ReactElement, type ReactNode, useRef, useState } from "react";
import { createRoutesStub } from "react-router";
import { localeLoader } from "@/i18n";
import type { Locale } from "@/i18n/locales";
import { messages as enMessages } from "@/locales/en/messages.po";
import { messages as nlMessages } from "@/locales/nl/messages.po";

// Catalogues are imported statically so tests can switch language synchronously,
// unlike the app, which loads them lazily per locale.
const catalogs = { nl: nlMessages, en: enMessages };

/**
 * Activates a locale for the assertions that follow. Call it in the test body
 * (or a `beforeEach`) whenever a test asserts on translated text.
 */
export function activateLocale(locale: Locale) {
   i18n.loadAndActivate({ locale, messages: catalogs[locale] });
}

type Options = Omit<RenderOptions, "wrapper"> & {
   locale?: Locale;
   /** Initial history entries for the router. */
   initialEntries?: string[];
   /** Route path to mount the element at, when the component reads route params. */
   path?: string;
   /** What the mounted route's loader hands the page, for components reading `useLoaderData`. */
   loaderData?: unknown;
   /** A pre-seeded client, for pages whose suspense queries have to resolve without a fetch. */
   queryClient?: QueryClient;
};

/**
 * Renders a component inside the providers the app itself mounts: query client,
 * router and i18n.
 */
export function renderWithProviders(
   ui: ReactElement,
   { locale = "nl", initialEntries, path, loaderData = null, queryClient, ...options }: Options = {},
) {
   activateLocale(locale);

   const client = queryClient ?? new QueryClient({ defaultOptions: { queries: { retry: false } } });

   const wrapper = ({ children }: { children: ReactNode }) => {
      // `createRoutesStub` returns a fresh component type per call, and the stub only
      // keeps its router across re-renders of the same type. Building it once — and
      // reading the children through a ref — keeps a re-render from remounting the tree.
      const childrenRef = useRef(children);
      childrenRef.current = children;

      const [Stub] = useState(() =>
         createRoutesStub([
            {
               id: "root",
               path: path ?? "*",
               loader: async () => {
                  // The app carries the locale loader on its root route, so anything that
                  // switches language has one to revalidate.
                  await localeLoader();
                  return loaderData;
               },
               Component: () => <>{childrenRef.current}</>,
            },
         ]),
      );

      return (
         <I18nProvider i18n={i18n}>
            <QueryClientProvider client={client}>
               {/* `activateLocale` above stands in for the catalogue the app loads before its first
                   render, so the stub hydrates rather than running the loader and rendering async. */}
               <Stub initialEntries={initialEntries} hydrationData={{ loaderData: { root: loaderData } }} />
            </QueryClientProvider>
         </I18nProvider>
      );
   };

   return render(ui, { wrapper, ...options });
}
