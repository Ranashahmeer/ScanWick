import { createFileRoute } from "@tanstack/react-router";
import * as z from "zod";
import { SharesPage } from "@/features/shares";

// Prototype screens 43 (manage shares) and 42 (create share link).
const searchSchema = z.object({
  view: z.enum(["manage", "create"]).optional(),
});

export const Route = createFileRoute("/_app/shares/")({
  validateSearch: searchSchema,
  component: RouteComponent,
});

function RouteComponent() {
  const { view } = Route.useSearch();
  return <SharesPage view={view} />;
}
