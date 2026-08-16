/**
 * Verify OTP — prototype screen 04.
 *
 * Security requirement carried over verbatim from the prototype: verifying
 * an OTP must never on its own issue a session for an account that already
 * has a password. This screen is only reachable straight after registration
 * (where the password was just set on this device) or when /login returns
 * 403 for an unverified account — it is never an alternative to signing in.
 */

import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "@tanstack/react-router";
import { isAxiosError } from "axios";

import { Btn } from "@/components/sw";
import { authClient } from "@/lib/api-client";
import { setTokens } from "@/lib/auth-tokens";
import { authStore, type AuthUser } from "@/lib/auth-store";
import {
  AuthAlert,
  AuthForm,
  AuthLayout,
  OtpBoxes,
  maskEmail,
} from "@/features/auth/components/auth-layout";

interface TokenResponse {
  access_token: string;
  refresh_token: string;
}

const RESEND_SECONDS = 42;

function errorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.detail === "string") {
    return error.response.data.detail;
  }
  return fallback;
}

export default function OtpCard({ email, plan }: { email: string; plan?: "free" | "basic" | "premium" }) {
  const navigate = useNavigate();
  const [alert, setAlert] = useState<{ message: string; tone: "success" | "failure" } | null>(null);
  const [code, setCode] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [resending, setResending] = useState(false);
  const [cooldown, setCooldown] = useState(RESEND_SECONDS);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = window.setInterval(() => setCooldown((s) => (s > 0 ? s - 1 : 0)), 1000);
    return () => window.clearInterval(timer);
  }, [cooldown]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (verifying || code.length !== 6) return;
    setVerifying(true);
    setAlert(null);

    try {
      const { data: tokens } = await authClient.post<TokenResponse>("/verify-otp", {
        email,
        otp: code,
        purpose: "verification",
      });
      setTokens({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });

      // OTP verification itself has already succeeded and tokens are issued
      // at this point — a failure here is NOT an invalid/expired-code
      // problem, so it must not be reported as one.
      try {
        const { data: user } = await authClient.get<AuthUser>("/me");
        authStore.setAuthenticated(user);

        // A paid plan was picked back on the landing page before this
        // account even existed — carry it through to checkout now instead
        // of dropping it and making them find their way to Billing.
        if (plan === "basic" || plan === "premium") {
          navigate({ to: "/account", search: { tab: "billing", upgrade: plan } });
        } else {
          navigate({ to: "/upload" });
        }
      } catch {
        setAlert({ message: "Signed in, but couldn't load your profile — please try again.", tone: "failure" });
      }
    } catch (error) {
      setAlert({ message: errorMessage(error, "Invalid or expired code."), tone: "failure" });
    } finally {
      setVerifying(false);
    }
  }

  async function handleResend() {
    if (resending || cooldown > 0) return;
    setResending(true);
    try {
      await authClient.post("/resend-otp", { email, purpose: "verification" });
      setAlert({ message: "A new code has been sent.", tone: "success" });
      setCooldown(RESEND_SECONDS);
    } catch (error) {
      setAlert({ message: errorMessage(error, "Could not resend the code."), tone: "failure" });
    } finally {
      setResending(false);
    }
  }

  const mmss = `${Math.floor(cooldown / 60)}:${String(cooldown % 60).padStart(2, "0")}`;

  return (
    <AuthLayout
      title="Check your email"
      sub={`We sent a 6-digit code to ${maskEmail(email)}`}
      alert={alert ? <AuthAlert {...alert} /> : undefined}
    >
      <div style={{ textAlign: "center" }}>
        <AuthForm onSubmit={onSubmit}>
          <OtpBoxes value={code} onChange={setCode} />
          <Btn type="submit" block disabled={verifying || code.length !== 6}>
            {verifying ? "Verifying…" : "Verify"}
          </Btn>
        </AuthForm>

        <div className="hint" style={{ marginTop: 12 }}>
          Didn't get it?{" "}
          <button
            type="button"
            onClick={handleResend}
            disabled={resending || cooldown > 0}
            style={{
              background: "none",
              border: 0,
              padding: 0,
              font: "inherit",
              color: cooldown > 0 ? "var(--ink3)" : "var(--g700)",
              fontWeight: 600,
              cursor: cooldown > 0 ? "default" : "pointer",
            }}
          >
            {resending ? "Sending…" : cooldown > 0 ? `Resend in ${mmss}` : "Resend the code"}
          </button>
        </div>
      </div>
    </AuthLayout>
  );
}
