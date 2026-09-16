import type { ButtonHTMLAttributes, PropsWithChildren } from "react";
import { twMerge } from "tailwind-merge";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
   className?: string;
};

export default function Button({ className, children, ...props }: PropsWithChildren<ButtonProps>) {
   return (
      <button
         className={twMerge(
            "rounded-sm bg-white hover:bg-blue-500 text-blue-500 hover:text-white border border-blue-500 py-3 px-4 flex flex-row gap-2 items-center",
            className,
         )}
         {...props}
      >
         {children}
      </button>
   );
}
