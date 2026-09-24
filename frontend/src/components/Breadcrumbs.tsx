import { Trans, useLingui } from "@lingui/react/macro";
import { Children, isValidElement, type PropsWithChildren } from "react";
import { Link, useLocation } from "react-router";
import { appRoutes } from "@/utils/routes.ts";

export function Breadcrumbs({ children }: PropsWithChildren) {
   const { t } = useLingui();
   const hasHome = Children.toArray(children).some(
      (child) => isValidElement<{ to?: string }>(child) && child.props.to === appRoutes.home(),
   );

   return (
      <nav className="mb-2 py-3 sm:mb-9" aria-label={t`Kruimelpad`}>
         <ol className="flex flex-wrap items-center gap-1">
            {!hasHome && (
               <BreadcrumbItem key="home" to={appRoutes.home()}>
                  <Trans>Home</Trans>
               </BreadcrumbItem>
            )}
            {children}
         </ol>
      </nav>
   );
}

export function BreadcrumbItem({ to, children }: PropsWithChildren<{ to: string }>) {
   const { pathname } = useLocation();

   return (
      <li className="group flex items-center gap-1">
         <Link to={to} className="text-nowrap" aria-current={pathname === to ? "page" : undefined}>
            {children}
         </Link>
         <span className="text-muted text-xs group-last:hidden" aria-hidden="true">
            {">"}
         </span>
      </li>
   );
}
