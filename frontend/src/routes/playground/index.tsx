import Playground from "@/features/playground";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/playground/")({
  component: Playground,
});
