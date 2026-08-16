import { createFileRoute } from "@tanstack/react-router";
import * as z from "zod";
import { MoneyPage } from "@/features/money";

// `view` selects which of the prototype's Surface 1 screens (18–31, 63, 64)
// is shown. Keeping them on one route means the account picker and the
// coverage rules are shared rather than restated per screen.
const moneySearchSchema = z.object({
  view: z
    .enum([
      "consolidated",
      "coverage",
      "spending",
      "payees",
      "recurring",
      "fees",
      "income",
      "stability",
      "seasonality",
      "classify",
      "balance",
      "obligations",
      "playbook",
      "readiness",
    ])
    .optional(),
});

export const Route = createFileRoute("/_app/money/")({
  validateSearch: moneySearchSchema,
  component: RouteComponent,
});

function RouteComponent() {
  const { view } = Route.useSearch();
  return <MoneyPage view={view} />;
}
