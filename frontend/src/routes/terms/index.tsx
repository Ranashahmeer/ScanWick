import { createFileRoute } from "@tanstack/react-router";
import { TermsOfServicePage } from "@/features/legal/terms-of-service";

export const Route = createFileRoute("/terms/")({
  component: TermsOfServicePage,
});
