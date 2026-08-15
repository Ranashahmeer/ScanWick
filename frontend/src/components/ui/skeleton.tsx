import { cn } from "@/lib/utils"

// A pulsing placeholder block shaped like the content that's about to
// arrive — for whole-page/card loading states. Pair with Spinner
// (spinner.tsx) for button/action-pending states instead, which reads
// better for "something you just triggered is in progress" than a
// skeleton does.
export function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="skeleton" className={cn("animate-pulse rounded-md bg-muted", className)} {...props} />
}
