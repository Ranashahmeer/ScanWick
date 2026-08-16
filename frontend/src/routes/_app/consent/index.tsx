import { createFileRoute } from "@tanstack/react-router";
import { ConsentPage } from "@/features/consent";

// Prototype screen 51 — the borrower's own consent centre.
export const Route = createFileRoute("/_app/consent/")({
  component: ConsentPage,
});
