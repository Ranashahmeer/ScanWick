import { createFileRoute } from "@tanstack/react-router";
import { EmailCard } from "@/features/auth/reset-password";
import { requireGuest } from "@/lib/auth-guards";

export const Route = createFileRoute("/_auth/getcode")({
  beforeLoad: requireGuest,
  component: RouteComponent,
});

function RouteComponent() {
  return <EmailCard />;
}
