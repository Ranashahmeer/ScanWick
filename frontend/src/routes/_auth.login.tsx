import { createFileRoute } from "@tanstack/react-router";
import * as z from "zod";
import Login from "@/features/auth/login";
import { requireGuest } from "@/lib/auth-guards";

const loginSearchSchema = z.object({
  redirect: z.string().optional(),
});

export const Route = createFileRoute("/_auth/login")({
  validateSearch: loginSearchSchema,
  beforeLoad: requireGuest,
  component: RouteComponent,
});

function RouteComponent() {
  const { redirect } = Route.useSearch();
  return <Login redirectTo={redirect} />;
}
