import * as React from "react";

import { cn } from "@/lib/utils";

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        className={cn(
          "flex h-12 w-full rounded-full border border-white/12 bg-white/6 px-4 py-2 text-sm text-[color:var(--foreground)] shadow-inner shadow-black/10 transition-colors outline-none placeholder:text-[color:var(--muted-foreground)] focus-visible:border-white/30 focus-visible:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
        type={type}
        ref={ref}
        {...props}
      />
    );
  },
);

Input.displayName = "Input";

export { Input };
