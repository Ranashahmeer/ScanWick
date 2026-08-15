import { createFileRoute } from "@tanstack/react-router";
import * as z from "zod";
import Register from "@/features/auth/register";
import { requireGuest } from "@/lib/auth-guards";

const registerSearchSchema = z.object({
  plan: z.enum(["free", "basic", "premium"]).optional(),
});

export const Route = createFileRoute("/_auth/register")({
  validateSearch: registerSearchSchema,
  beforeLoad: requireGuest,
  component: RouteComponent,
});

function RouteComponent() {
  const { plan } = Route.useSearch();

  return <Register plan={plan} />;
}
