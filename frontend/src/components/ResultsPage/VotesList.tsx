import { faChevronRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans } from "@lingui/react/macro";
import type { PropsWithChildren } from "react";
import { Link } from "react-router";
import { twMerge } from "tailwind-merge";
import { useFormatters } from "../../utils/format";

type VotesListProps = {
   total?: {
      label: string;
      value: number;
   };
   indexColumn: string;
};

export default function VotesList({ total, indexColumn, children }: PropsWithChildren<VotesListProps>) {
   const { formatNumber } = useFormatters();

   // Use `overflow-visible w-1 text-nowrap` to ignore the width of the spanned rows for the max-content col size
   return (
      <div className="votes-cast-list-container">
         <div className="grid grid-cols-[max-content_auto_max-content_max-content] gap-x-2 sm:gap-x-4">
            <div className="col-span-3 flex justify-between py-3 pl-4.5 font-semibold">
               <span className="w-1 overflow-visible text-nowrap">{indexColumn}</span>
               <span>
                  <Trans>Aantal stemmen</Trans>
               </span>
            </div>
            {children}

            {total && (
               <div className="col-span-3 flex h-18 items-center justify-between py-3 pl-6 font-semibold">
                  <span className="w-1 overflow-visible text-nowrap">{total.label}</span>
                  <span>{formatNumber(total.value)}</span>
               </div>
            )}
         </div>
      </div>
   );
}

type VotesListItemProps = {
   number: number | null;
   title: string;
   voteCount: number;
   href?: string;
};

export function VotesListItem({ number, title, voteCount, href }: VotesListItemProps) {
   const isClickable = voteCount > 0 && !!href;
   const { formatNumber } = useFormatters();

   const className = twMerge(
      "hover:no-underline! col-span-4 grid h-18 grid-cols-subgrid items-center pr-4 pl-6 even:bg-blue-50",
      isClickable && "hover:bg-blue-100",
   );

   const content = (
      <>
         <span className="font-light text-gray-700">{number ?? "-"}</span>
         <span className="in-[a]:text-blue-500 in-[a]:underline">{title}</span>
         <span className={twMerge("text-right font-number", voteCount && "font-semibold text-gray-700")}>
            {voteCount ? formatNumber(voteCount) : "–"}
         </span>
         <span>{isClickable && <FontAwesomeIcon icon={faChevronRight} />}</span>
      </>
   );

   return isClickable ? (
      <Link to={href} className={className}>
         {content}
      </Link>
   ) : (
      <div className={className}>{content}</div>
   );
}
