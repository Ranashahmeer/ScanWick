import { createFileRoute } from "@tanstack/react-router";
import * as z from "zod";
import OtpCard from "@/features/auth/otp";
import { requireGuest } from "@/lib/auth-guards";

const otpSearchSchema = z.object({
  email: z.string().email(),
  plan: z.enum(["free", "basic", "premium"]).optional(),
});

export const Route = createFileRoute("/_auth/otp")({
  validateSearch: otpSearchSchema,
  beforeLoad: requireGuest,
  component: RouteComponent,
});

function RouteComponent() {
  const { email, plan } = Route.useSearch();
  return <OtpCard email={email} plan={plan} />;
}
