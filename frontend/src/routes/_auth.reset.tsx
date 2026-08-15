import { createFileRoute } from "@tanstack/react-router";
import * as z from "zod";
import { ResetCard } from "@/features/auth/reset-password";
import { requireGuest } from "@/lib/auth-guards";

const resetSearchSchema = z.object({
  token: z.string(),
});

export const Route = createFileRoute("/_auth/reset")({
  validateSearch: resetSearchSchema,
  beforeLoad: requireGuest,
  component: RouteComponent,
});

function RouteComponent() {
  const { token } = Route.useSearch();
  return <ResetCard token={token} />;
}
