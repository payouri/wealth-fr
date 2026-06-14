// Switch primitive — Radix behaviour on the DESIGN.md tokens. Slate-teal when
// on, panel when off; the focus ring matches every other control.
import { Switch as SwitchPrimitive } from "radix-ui";
import type * as React from "react";
import { cn } from "@/lib/utils";

export function Switch({ className, ...props }: React.ComponentProps<typeof SwitchPrimitive.Root>) {
  return (
    <SwitchPrimitive.Root
      className={cn(
        // `before` expands the tap target to ~44px without enlarging the track.
        "peer relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border border-transparent transition-colors",
        "before:absolute before:-inset-x-2 before:-inset-y-3 before:content-['']",
        // Off-track neutral derived from tokens (not a magic literal).
        "bg-[color-mix(in_oklch,var(--muted-foreground),var(--background)_68%)] data-[state=checked]:bg-primary",
        "outline-none focus-visible:ring-2 focus-visible:ring-ring/60 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    >
      <SwitchPrimitive.Thumb
        className={cn(
          "pointer-events-none block size-4 rounded-full bg-background shadow-sm transition-transform",
          "translate-x-0.5 data-[state=checked]:translate-x-[18px]",
        )}
      />
    </SwitchPrimitive.Root>
  );
}
