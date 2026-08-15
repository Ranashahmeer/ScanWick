import { createFileRoute } from "@tanstack/react-router";
import * as z from "zod";
import { AccountSettingsPage } from "@/features/account";

// `tab`/`upgrade` are how the landing page's pricing CTAs and the post-
// checkout redirect deep-link straight into the right sub-tab (see
// AccountSettingsPage/AccountBilling, which read these). `reference` isn't
// declared here on purpose — it's Paystack/Flutterwave's own redirect
// param, read directly off window.location.search by SubscriptionTab so it
// still works even though this schema doesn't know its shape.
const accountSearchSchema = z.object({
  tab: z.enum(["billing", "team", "markers", "settings"]).optional(),
  upgrade: z.enum(["basic", "premium"]).optional(),
});

export const Route = createFileRoute("/_app/account/")({
  validateSearch: accountSearchSchema,
  component: AccountSettingsPage,
});
