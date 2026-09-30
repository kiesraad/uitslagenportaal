import type { AnchorHTMLAttributes, ButtonHTMLAttributes } from "react";
import { twMerge } from "tailwind-merge";
import { tw } from "@/utils/tw.ts";

const buttonClasses = tw`hover:no-underline! flex w-fit cursor-pointer flex-row items-center gap-2 rounded-xs border border-blue-500 px-4 py-3 focus-visible:outline-2 focus-visible:outline-blue-400 disabled:cursor-default disabled:opacity-75`;

const variantClasses = {
   default: tw`bg-white text-blue-500! not-disabled:hover:bg-blue-500 not-disabled:hover:text-white! disabled:bg-gray-100 disabled:text-blue-500!`,
   inverted: tw`bg-blue-500 text-white! not-disabled:hover:bg-blue-600 disabled:bg-blue-400`,
};

type ButtonVariant = keyof typeof variantClasses;

type ButtonProps = { variant?: ButtonVariant } & (
   | (ButtonHTMLAttributes<HTMLButtonElement> & { href?: never })
   | (AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; disabled?: boolean })
);

export default function Button({ variant = "default", ...props }: ButtonProps) {
   if (props.href !== undefined) {
      const { className, disabled, href, children, ...anchorProps } = props;
      const classes = twMerge(buttonClasses, variantClasses[variant], className);
      // An <a> has no disabled state, so a disabled link becomes a disabled button, which screen readers announce.
      if (disabled) {
         return (
            <button type="button" className={classes} disabled>
               {children}
            </button>
         );
      }

      return (
         <a className={classes} href={href} {...anchorProps}>
            {children}
         </a>
      );
   }

   const { className, disabled, ...buttonProps } = props;
   return (
      <button
         className={twMerge(buttonClasses, variantClasses[variant], className)}
         disabled={disabled}
         {...buttonProps}
      />
   );
}
