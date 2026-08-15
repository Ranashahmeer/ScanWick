import { Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

// Small circular progress indicator for "an action is in flight" states
// (a button that was just clicked, a mutation in progress) — pair with
// Skeleton (skeleton.tsx) for "content hasn't loaded yet" states instead,
// which reads better for whole-page/section loading than a spinner does.
export function Spinner({ className, size = 14 }: { className?: string; size?: number }) {
  return <Loader2 size={size} className={cn("animate-spin", className)} aria-hidden="true" />
}

// Spinner + label, inline — the common case of a button showing "Doing
// thing…" while its mutation is pending. Kept as one component so every
// pending-button label in the app looks and behaves identically.
export function LoadingLabel({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center justify-center gap-1.5">
      <Spinner />
      {label}
    </span>
  )
}
