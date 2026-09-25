import type { PropsWithChildren } from "react";
import { twMerge } from "tailwind-merge";

/**
 * Simple <section> with preset padding to keep it consistent among
 */
export default function PageSection({ className, children }: PropsWithChildren<{ className?: string }>) {
   return <section className={twMerge("px-5 py-4 sm:px-10 sm:py-6 lg:px-24 lg:py-8", className)}>{children}</section>;
}
