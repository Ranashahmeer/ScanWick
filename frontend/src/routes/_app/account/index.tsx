import { createFileRoute } from "@tanstack/react-router";
import * as z from "zod";
import { AccountSettingsPage } from "@/features/account";

// `tab` selects the prototype's account screens — 57 profile, 67 security,
// 66 billing, 55 plans, 68 delete — plus the two workspace panels that have
// no prototype screen of their own. `upgrade` is how the pricing CTAs and
// the post-checkout redirect deep-link straight into checkout.
//
// `reference` isn't declared here on purpose — it's the payment provider's
// own redirect param, read directly off window.location.search by the
// billing tab so it still works even though this schema doesn't know it.
const accountSearchSchema = z.object({
  tab: z.enum(["profile", "security", "billing", "plans", "delete", "markers", "settings"]).optional(),
  upgrade: z.enum(["basic", "premium"]).optional(),
});

export const Route = createFileRoute("/_app/account/")({
  validateSearch: accountSearchSchema,
  component: AccountSettingsPage,
});
