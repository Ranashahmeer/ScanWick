import { createFileRoute } from "@tanstack/react-router";
import * as z from "zod";
import { AuditPage } from "@/features/audit";

// Prototype screens 32 (account audit), 33 (borrower access trail), 34
// (institution access log) and 61 (analysis run record).
const searchSchema = z.object({
  view: z.enum(["account", "access-trail", "institution-log", "run-record"]).optional(),
});

export const Route = createFileRoute("/_app/audit/")({
  validateSearch: searchSchema,
  component: RouteComponent,
});

function RouteComponent() {
  const { view } = Route.useSearch();
  return <AuditPage view={view} />;
}
