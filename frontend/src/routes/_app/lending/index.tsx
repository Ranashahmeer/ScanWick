import { createFileRoute } from "@tanstack/react-router";
import * as z from "zod";
import { LendingPage } from "@/features/lending";

// Surface 2 — prototype screens 65, 35, 36, 37, 38, 39, 40 and 41.
const searchSchema = z.object({
  view: z
    .enum(["home", "assessments", "new", "signals", "brief", "traceability", "stacking", "type"])
    .optional(),
});

export const Route = createFileRoute("/_app/lending/")({
  validateSearch: searchSchema,
  component: RouteComponent,
});

function RouteComponent() {
  const { view } = Route.useSearch();
  return <LendingPage view={view} />;
}
