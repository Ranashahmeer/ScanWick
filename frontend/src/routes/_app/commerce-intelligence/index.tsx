import { createFileRoute } from "@tanstack/react-router";
import CommerceIntelligence from "@/features/commerce-intelligence";

export const Route = createFileRoute("/_app/commerce-intelligence/")({
  component: CommerceIntelligence,
});
