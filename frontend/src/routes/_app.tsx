import { createFileRoute, Outlet } from '@tanstack/react-router'
import { requireAuth } from '@/lib/auth-guards'

export const Route = createFileRoute('/_app')({
  beforeLoad: ({ location }) => requireAuth(location.href),
  component: RouteComponent,
})

function RouteComponent() {
  // Every page nested under /_app already renders its own complete chrome
  // (IntelligenceTopbar + sidebar, or AppTopbar) — this layout is auth-gating
  // only, not a visual shell.
  return <Outlet />
}
