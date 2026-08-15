import { createFileRoute } from "@tanstack/react-router";
import { HomePage } from "@/features/landing";

export const Route = createFileRoute("/")({
  component: HomePage,
});
