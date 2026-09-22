import { Trans } from "@lingui/react/macro";
import { Children, isValidElement, type PropsWithChildren } from "react";
import { Link } from "react-router";
import { appRoutes } from "@/utils/routes.ts";

export function Breadcrumbs({ children }: PropsWithChildren) {
   const hasHome = Children.toArray(children).some(
      (child) => isValidElement<{ to?: string }>(child) && child.props.to === appRoutes.home(),
   );

   return (
      <nav className="mb-2 flex items-center gap-1 overflow-x-auto py-3 sm:mb-9" aria-label="Breadcrumb">
         {!hasHome && (
            <BreadcrumbItem key="home" to={appRoutes.home()}>
               <Trans>Home</Trans>
            </BreadcrumbItem>
         )}
         {children}
      </nav>
   );
}

export function BreadcrumbItem({ to, children }: PropsWithChildren<{ to: string }>) {
   return (
      <>
         <span className="text-nowrap">
            <Link key="home" to={to}>
               {children}
            </Link>
         </span>
         <span className="text-muted text-xs last:hidden">{">"}</span>
      </>
   );
}
