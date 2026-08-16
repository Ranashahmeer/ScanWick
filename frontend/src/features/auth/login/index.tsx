/**
 * Sign in — prototype screen 03.
 *
 * Email and password, then the account's second factor where one is set.
 * The security requirement from screen 04 holds here too: a code alone must
 * never issue a session for an account that has a password, which is why
 * /2fa/verify-login re-sends the password alongside the code.
 *
 * Failure copy is deliberately generic — the prototype's states table
 * requires one message that never reveals whether the email exists.
 */

import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { isAxiosError } from "axios";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";

import { Btn, Field, Inp } from "@/components/sw";
import { authClient } from "@/lib/api-client";
import { setTokens } from "@/lib/auth-tokens";
import { authStore, type AuthUser } from "@/lib/auth-store";
import {
  AuthAlert,
  AuthFootLink,
  AuthForm,
  AuthLayout,
  GoogleAuth,
  PasswordInput,
} from "@/features/auth/components/auth-layout";

interface TokenResponse {
  access_token: string;
  refresh_token: string;
}

interface LoginResponse {
  access_token?: string;
  refresh_token?: string;
  message?: string;
  email?: string;
}

type Alert = { message: string; tone: "success" | "failure" } | null;

const formSchema = z.object({
  email: z.string().email("Enter your email as xyz@example.com"),
  password: z.string().nonempty("Password is required"),
});

type FormValues = z.infer<typeof formSchema>;

export default function Login({ redirectTo }: { redirectTo?: string }) {
  const navigate = useNavigate();
  const [alert, setAlert] = useState<Alert>(null);
  const [submitting, setSubmitting] = useState(false);
  const [keepSignedIn, setKeepSignedIn] = useState(true);

  // Set once /login responds with {message, email} instead of tokens —
  // meaning the password was correct but the account has TOTP 2FA enabled.
  // Held alongside the password (never sent anywhere except the follow-up
  // /2fa/verify-login call) since that endpoint re-checks it — a correct
  // TOTP code alone must never be enough on its own.
  const [pending2fa, setPending2fa] = useState<{ email: string; password: string } | null>(null);
  const [twoFactorCode, setTwoFactorCode] = useState("");
  const [verifying2fa, setVerifying2fa] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { email: "", password: "" },
  });

  async function completeLogin(accessToken: string, refreshToken: string) {
    setTokens({ accessToken, refreshToken });

    // Login itself has already succeeded and tokens are issued at this
    // point — a failure here is NOT a credentials problem, so it must not
    // be reported as one.
    try {
      const { data: user } = await authClient.get<AuthUser>("/me");
      authStore.setAuthenticated(user);

      // Land on Upload by default, not the dashboard — the dashboard only
      // makes sense once there's real analysis to show. redirectTo (set
      // when /_app's guard bounced an unauthenticated visit) still wins.
      navigate({ to: redirectTo || "/upload" });
    } catch {
      setAlert({ message: "Signed in, but couldn't load your profile — please try again.", tone: "failure" });
    }
  }

  async function onSubmit(data: FormValues) {
    if (submitting) return;
    setSubmitting(true);
    setAlert(null);

    try {
      const { data: result } = await authClient.post<LoginResponse>("/login", data);

      if (!result.access_token || !result.refresh_token) {
        setPending2fa({ email: data.email, password: data.password });
        return;
      }

      await completeLogin(result.access_token, result.refresh_token);
    } catch (error) {
      if (isAxiosError(error) && error.response?.status === 403) {
        // Account exists but hasn't completed email verification yet.
        navigate({ to: "/otp", search: { email: data.email } });
        return;
      }

      const message =
        isAxiosError(error) && typeof error.response?.data?.detail === "string"
          ? error.response.data.detail
          : "Invalid email or password.";
      setAlert({ message, tone: "failure" });
    } finally {
      setSubmitting(false);
    }
  }

  async function onSubmit2fa(event: FormEvent) {
    event.preventDefault();
    if (!pending2fa || verifying2fa) return;
    setVerifying2fa(true);

    try {
      const { data: tokens } = await authClient.post<TokenResponse>("/2fa/verify-login", {
        email: pending2fa.email,
        password: pending2fa.password,
        code: twoFactorCode,
      });
      await completeLogin(tokens.access_token, tokens.refresh_token);
    } catch (error) {
      const message =
        isAxiosError(error) && typeof error.response?.data?.detail === "string"
          ? error.response.data.detail
          : "Invalid two-factor code.";
      setAlert({ message, tone: "failure" });
    } finally {
      setVerifying2fa(false);
    }
  }

  if (pending2fa) {
    return (
      <AuthLayout
        title="Two-factor authentication"
        sub={`Enter the 6-digit code from your authenticator app for ${pending2fa.email}`}
        alert={alert ? <AuthAlert {...alert} /> : undefined}
      >
        <AuthForm onSubmit={onSubmit2fa}>
          <Field label="Authentication code" id="totp">
            <Inp
              id="totp"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={twoFactorCode}
              onChange={(e) => setTwoFactorCode(e.target.value.replace(/\D/g, ""))}
              placeholder="000000"
              style={{ fontFamily: "var(--mono)", fontSize: 19, letterSpacing: "6px", textAlign: "center" }}
            />
          </Field>
          <Btn type="submit" block disabled={verifying2fa || twoFactorCode.length !== 6}>
            {verifying2fa ? "Verifying…" : "Verify"}
          </Btn>
        </AuthForm>
        <AuthFootLink desc="Wrong account?" link="Back to sign in" onClick={() => setPending2fa(null)} />
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Welcome back"
      sub="Sign in to your Scanwick account."
      alert={alert ? <AuthAlert {...alert} /> : undefined}
    >
      <AuthForm onSubmit={form.handleSubmit(onSubmit)}>
        <Controller
          name="email"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field label="Email" id="email" error={fieldState.error?.message}>
              <Inp
                id="email"
                type="email"
                autoComplete="email"
                placeholder="adaeze.n@example.com"
                invalid={!!fieldState.error}
                {...field}
              />
            </Field>
          )}
        />

        <Controller
          name="password"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field label="Password" id="password" error={fieldState.error?.message}>
              <PasswordInput
                id="password"
                name={field.name}
                value={field.value}
                onChange={field.onChange}
                onBlur={field.onBlur}
                autoComplete="current-password"
                invalid={!!fieldState.error}
              />
            </Field>
          )}
        />

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", margin: "6px 0 16px", gap: 12 }}>
          <label style={{ fontSize: 12, display: "flex", gap: 7, alignItems: "center", cursor: "pointer" }}>
            <input type="checkbox" checked={keepSignedIn} onChange={(e) => setKeepSignedIn(e.target.checked)} /> Keep me
            signed in
          </label>
          <Link to="/getcode" style={{ fontSize: 12, color: "var(--g700)", fontWeight: 600 }}>
            Forgot password?
          </Link>
        </div>

        <Btn type="submit" block disabled={submitting}>
          {submitting ? "Signing in…" : "Continue"}
        </Btn>
      </AuthForm>

      <GoogleAuth label="Sign in with Google" />
      <AuthFootLink desc="New here?" link="Create an account" to="/register" />
    </AuthLayout>
  );
}
