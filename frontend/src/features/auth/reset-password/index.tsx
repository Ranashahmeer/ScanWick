/**
 * Reset password — prototype screen 05.
 *
 * Three steps: request, verify, set new. The prototype's rule for step 1 is
 * that the confirmation reads the same whether or not the address exists,
 * and that all other sessions are signed out after a successful reset.
 *
 * The backend's /forgot-password does return an explicit account-state
 * message, so that message is shown when it is present rather than being
 * replaced with a hardcoded one — but the fallback stays non-disclosing.
 */

import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { isAxiosError } from "axios";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";

import { Btn, Field, Inp } from "@/components/sw";
import { authClient } from "@/lib/api-client";
import {
  AuthAlert,
  AuthFootLink,
  AuthForm,
  AuthLayout,
  PasswordInput,
} from "@/features/auth/components/auth-layout";

type Alert = { message: string; tone: "success" | "failure" } | null;

function errorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.detail === "string") {
    return error.response.data.detail;
  }
  return fallback;
}

/** Step 1 — request a reset code. */
const emailSchema = z.object({
  email: z.string().email("Email is required in format xyz@example.com"),
});

function EmailCard() {
  const [alert, setAlert] = useState<Alert>(null);
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  const form = useForm<z.infer<typeof emailSchema>>({
    resolver: zodResolver(emailSchema),
    defaultValues: { email: "" },
  });

  async function onSubmit(data: z.infer<typeof emailSchema>) {
    if (submitting) return;
    setSubmitting(true);
    setAlert(null);

    try {
      const response = await authClient.post("/forgot-password", { email: data.email });
      setAlert({
        message: response.data?.message ?? "If that address has an account, a reset link is on its way.",
        tone: "success",
      });
      setSent(true);
    } catch (error) {
      setAlert({ message: errorMessage(error, "Something went wrong. Please try again."), tone: "failure" });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title="Reset your password"
      sub="Enter your email and we will send you a link to set a new one."
      alert={alert ? <AuthAlert {...alert} /> : undefined}
    >
      <AuthForm onSubmit={form.handleSubmit(onSubmit)}>
        <Controller
          name="email"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field label="Email" id="reset-email" error={fieldState.error?.message}>
              <Inp
                id="reset-email"
                type="email"
                autoComplete="email"
                placeholder="adaeze.n@example.com"
                invalid={!!fieldState.error}
                {...field}
              />
            </Field>
          )}
        />
        <Btn type="submit" block disabled={submitting}>
          {submitting ? "Sending…" : sent ? "Send it again" : "Send reset link"}
        </Btn>
      </AuthForm>
      <AuthFootLink desc="Remember your password?" link="Back to sign in" to="/login" />
    </AuthLayout>
  );
}

/** Step 3 — set the new password against the emailed token. */
const resetSchema = z
  .object({
    password: z.string().nonempty("Password is required").min(8, "Password must be at least 8 characters"),
    confirmPassword: z.string().nonempty("Confirm the password by retyping it"),
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: "Both passwords must match",
    path: ["confirmPassword"],
  });

function ResetCard({ token }: { token: string }) {
  const navigate = useNavigate();
  const [alert, setAlert] = useState<Alert>(null);
  const [submitting, setSubmitting] = useState(false);

  const form = useForm<z.infer<typeof resetSchema>>({
    resolver: zodResolver(resetSchema),
    defaultValues: { password: "", confirmPassword: "" },
  });

  async function onSubmit(data: z.infer<typeof resetSchema>) {
    if (submitting) return;
    setSubmitting(true);
    setAlert(null);

    try {
      await authClient.post("/reset-password", { token, new_password: data.password });
      setAlert({ message: "Password updated. Please sign in again.", tone: "success" });
      navigate({ to: "/login" });
    } catch (error) {
      setAlert({ message: errorMessage(error, "Reset link is invalid or has expired."), tone: "failure" });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title="Choose a new password"
      sub="At least 8 characters. You will be signed out of every other device."
      alert={alert ? <AuthAlert {...alert} /> : undefined}
    >
      <AuthForm onSubmit={form.handleSubmit(onSubmit)}>
        <Controller
          name="password"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field label="New password" id="new-password" error={fieldState.error?.message}>
              <PasswordInput
                id="new-password"
                name={field.name}
                value={field.value}
                onChange={field.onChange}
                onBlur={field.onBlur}
                autoComplete="new-password"
                invalid={!!fieldState.error}
              />
            </Field>
          )}
        />
        <Controller
          name="confirmPassword"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field label="Confirm new password" id="confirm-password" error={fieldState.error?.message}>
              <PasswordInput
                id="confirm-password"
                name={field.name}
                value={field.value}
                onChange={field.onChange}
                onBlur={field.onBlur}
                autoComplete="new-password"
                invalid={!!fieldState.error}
              />
            </Field>
          )}
        />
        <Btn type="submit" block disabled={submitting}>
          {submitting ? "Updating…" : "Set password"}
        </Btn>
      </AuthForm>
      <AuthFootLink desc="Changed your mind?" link="Back to sign in" to="/login" />
    </AuthLayout>
  );
}

export { EmailCard, ResetCard };
