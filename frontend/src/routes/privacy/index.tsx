import { createFileRoute } from "@tanstack/react-router";
import { PrivacyPolicyPage } from "@/features/legal/privacy-policy";

export const Route = createFileRoute("/privacy/")({
  component: PrivacyPolicyPage,
});
