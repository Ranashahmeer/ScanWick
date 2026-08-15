import { createFileRoute } from "@tanstack/react-router";
import * as z from "zod";
import { AcceptInvitePage } from "@/features/auth/accept-invite";

// Deliberately public, no beforeLoad guard: an already-authenticated user
// confirms the invite as themselves, an anonymous visitor creates a brand
// new account as part of accepting it — AcceptInvitePage branches on
// useAuth()'s status itself rather than a route-level guard picking one
// path for everyone (unlike /login, /register, /reset, which only ever
// make sense logged out).
const acceptInviteSearchSchema = z.object({
  token: z.string(),
});

export const Route = createFileRoute("/accept-invite")({
  validateSearch: acceptInviteSearchSchema,
  component: RouteComponent,
});

function RouteComponent() {
  const { token } = Route.useSearch();
  return <AcceptInvitePage token={token} />;
}
