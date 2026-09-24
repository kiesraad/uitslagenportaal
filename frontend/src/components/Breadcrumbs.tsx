import { faChevronRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans, useLingui } from "@lingui/react/macro";
import { Children, isValidElement, type PropsWithChildren } from "react";
import { Link } from "react-router";
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

export function BreadcrumbItem({ to, children }: PropsWithChildren<{ to?: string }>) {
   return (
      <li className="group group flex items-center gap-1 text-nowrap max-sm:not-last:max-w-1/2">
         {to ? (
            <Link key="home" to={to} className="overflow-hidden text-ellipsis">
               {children}
            </Link>
         ) : (
            <span>{children}</span>
         )}
         <span className="text-muted text-xs group-last:hidden">
            <FontAwesomeIcon icon={faChevronRight} />
         </span>
      </li>
   );
}
