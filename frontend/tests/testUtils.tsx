import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type RenderOptions, render } from "@testing-library/react";
import { createContext, type ReactElement, type ReactNode, use, useState } from "react";
import { createRoutesStub, Outlet } from "react-router";
import { LocaleProvider } from "@/components/LocaleProvider";
import { getI18n, localeLoader } from "@/i18n";
import type { Locale } from "@/i18n/locales";
import { messages as enMessages } from "@/locales/en/messages.po";
import { messages as nlMessages } from "@/locales/nl/messages.po";

// Catalogues are imported statically so tests can switch language synchronously,
// unlike the app, which loads them lazily per locale.
const catalogs = { nl: nlMessages, en: enMessages };

/**
 * Loads a locale's catalogue into its instance and returns that instance. Call it in the test body
 * (or a `beforeEach`) whenever a test asserts on translated text outside `renderWithProviders`.
 */
export function activateLocale(locale: Locale) {
   const i18n = getI18n(locale);
   i18n.loadAndActivate({ locale, messages: catalogs[locale] });
   return i18n;
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

const ChildrenContext = createContext<ReactNode>(null);

function RouteChildren() {
   return use(ChildrenContext);
}

function RootLayout() {
   return (
      <LocaleProvider>
         <Outlet />
      </LocaleProvider>
   );
}

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
      // passing the children through context — keeps a re-render from remounting the tree.
      // The root route mirrors the app's: its locale loader is what a language switch revalidates.
      const [Stub] = useState(() =>
         createRoutesStub([
            {
               id: "root",
               loader: localeLoader,
               Component: RootLayout,
               children: [
                  {
                     id: "page",
                     path: path ?? "*",
                     loader: () => loaderData,
                     Component: RouteChildren,
                  },
               ],
            },
         ]),
      );

      return (
         <QueryClientProvider client={client}>
            {/* `activateLocale` above stands in for the catalogue the app loads before its first
                render, so the stub hydrates rather than running the loaders and rendering async. */}
            <ChildrenContext value={children}>
               <Stub
                  initialEntries={initialEntries}
                  hydrationData={{ loaderData: { root: { locale }, page: loaderData } }}
               />
            </ChildrenContext>
         </QueryClientProvider>
      );
   };

   return render(ui, { wrapper, ...options });
}
