import { createFileRoute } from "@tanstack/react-router";
import * as z from "zod";
import { InstitutionPage } from "@/features/institution";

// Prototype screens 53 (team & roles), 54 (credit ledger) and 56 (API).
const searchSchema = z.object({
  view: z.enum(["team", "credits", "api"]).optional(),
});

export const Route = createFileRoute("/_app/institution/")({
  validateSearch: searchSchema,
  component: RouteComponent,
});

function RouteComponent() {
  const { view } = Route.useSearch();
  return <InstitutionPage view={view} />;
}
