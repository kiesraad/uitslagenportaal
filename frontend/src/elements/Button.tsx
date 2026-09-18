import type { AnchorHTMLAttributes, ButtonHTMLAttributes } from "react";
import { twMerge } from "tailwind-merge";
import { tw } from "@/utils/tw.ts";

type ButtonProps =
   | (ButtonHTMLAttributes<HTMLButtonElement> & { href?: never })
   | (AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; disabled?: boolean });

const buttonClasses = tw`hover:no-underline! flex w-fit cursor-pointer flex-row items-center gap-2 rounded-sm border border-blue-700 bg-white px-4 py-3 text-blue-700! hover:bg-blue-700 hover:text-white!`;
const disabledClasses = tw`cursor-default bg-gray-100 opacity-75 hover:bg-gray-100 hover:text-blue-700`;

export default function Button(props: ButtonProps) {
   if (props.href !== undefined) {
      const { className, disabled, href, ...anchorProps } = props;
      // An <a> has no disabled state; without an href it is neither focusable nor clickable.
      return (
         <a
            className={twMerge(buttonClasses, disabled && disabledClasses, className)}
            href={disabled ? undefined : href}
            aria-disabled={disabled || undefined}
            {...anchorProps}
         />
      );
   }

   const { className, disabled, ...buttonProps } = props;
   return (
      <button
         className={twMerge(buttonClasses, disabled && disabledClasses, className)}
         disabled={disabled}
         {...buttonProps}
      />
   );
}
