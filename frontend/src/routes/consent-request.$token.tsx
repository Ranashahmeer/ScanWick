import { createFileRoute } from "@tanstack/react-router";
import { ConsentRequestView } from "@/features/public-links";

// Prototype screen 52 — what a borrower receives when a lender initiates an
// assessment. Public and mobile-first: consent comes first, an account after.
export const Route = createFileRoute("/consent-request/$token")({
  component: RouteComponent,
});

function RouteComponent() {
  const { token } = Route.useParams();
  return <ConsentRequestView token={token} />;
}
