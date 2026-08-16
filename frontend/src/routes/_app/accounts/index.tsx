import { createFileRoute } from "@tanstack/react-router";
import * as z from "zod";
import { AccountsPage } from "@/features/accounts";

// Prototype screen 06 by default; `view=health` is screen 15, which also
// carries screen 16's borrower/lender pair when something has lapsed.
const searchSchema = z.object({
  view: z.enum(["add", "health"]).optional(),
});

export const Route = createFileRoute("/_app/accounts/")({
  validateSearch: searchSchema,
  component: RouteComponent,
});

function RouteComponent() {
  const { view } = Route.useSearch();
  return <AccountsPage view={view} />;
}
