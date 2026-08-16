import { createFileRoute } from "@tanstack/react-router";
import * as z from "zod";
import CommerceIntelligence from "@/features/commerce-intelligence";

// Prototype screens 58 (connect trading records) and 59 (cash-gap
// verification) — the only two e-commerce capabilities still in scope.
const searchSchema = z.object({
  view: z.enum(["connect", "cash-gap"]).optional(),
});

export const Route = createFileRoute("/_app/commerce-intelligence/")({
  validateSearch: searchSchema,
  component: RouteComponent,
});

function RouteComponent() {
  const { view } = Route.useSearch();
  return <CommerceIntelligence view={view} />;
}
