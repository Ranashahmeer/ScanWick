import { createFileRoute } from "@tanstack/react-router";
import * as z from "zod";
import { PortfolioPage } from "@/features/portfolio";

// Surface 3 — prototype screens 46, 45, 47, 48 and 49.
const searchSchema = z.object({
  view: z.enum(["portfolio", "consent", "facility", "signal", "acknowledge"]).optional(),
});

export const Route = createFileRoute("/_app/portfolio/")({
  validateSearch: searchSchema,
  component: RouteComponent,
});

function RouteComponent() {
  const { view } = Route.useSearch();
  return <PortfolioPage view={view} />;
}
