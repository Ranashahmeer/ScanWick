import { createFileRoute } from "@tanstack/react-router";
import { RecipientView } from "@/features/public-links";

// Prototype screen 44 — what a named recipient sees when they open a share
// link. Public on purpose: no Scanwick account is needed.
export const Route = createFileRoute("/v/$ref")({
  component: RouteComponent,
});

function RouteComponent() {
  const { ref } = Route.useParams();
  return <RecipientView reference={ref} />;
}
