/**
 * Create account — prototype screen 02.
 *
 * The consent checkbox here is ACCOUNT_CONNECTION consent only. It does not
 * authorise analysis, sharing or monitoring — those are separate consent
 * events captured later, each with its own record and its own versioned
 * text. Never bundle them into this checkbox.
 */

import { useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
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
  GoogleAuth,
  PasswordInput,
} from "@/features/auth/components/auth-layout";

const planLabels = {
  free: "Free",
  basic: "Basic",
  premium: "Premium",
} as const;

const formSchema = z.object({
  fullName: z.string().nonempty("Full name is required"),
  email: z.string().email("Email should be in format xyz@example.com"),
  phone: z
    .string()
    .nonempty("Phone number is required")
    .regex(/^(0\d{10}|\+234\d{10}|234\d{10})$/, "Use a Nigerian format: 0803…, +234 803…, 234803…"),
  password: z.string().nonempty("Password is required").min(10, "At least 10 characters."),
  consent: z
    .boolean()
    .refine((value) => value, { message: "Please accept the Terms of Service and Privacy Policy to continue." }),
});

type FormValues = z.infer<typeof formSchema>;

export default function Register({ plan }: { plan?: "free" | "basic" | "premium" }) {
  const navigate = useNavigate();
  const [alert, setAlert] = useState<{ message: string; tone: "success" | "failure" } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { fullName: "", email: "", phone: "", password: "", consent: false },
  });

  const password = form.watch("password");

  async function onSubmit(data: FormValues) {
    if (submitting) return;
    setSubmitting(true);
    setAlert(null);

    const [firstName, ...rest] = data.fullName.trim().split(/\s+/);
    const lastName = rest.join(" ") || firstName;

    try {
      await authClient.post("/register", {
        first_name: firstName,
        last_name: lastName,
        email: data.email,
        phone: data.phone,
        password: data.password,
      });
      navigate({ to: "/otp", search: { email: data.email, plan } });
    } catch (error) {
      const message =
        isAxiosError(error) && typeof error.response?.data?.detail === "string"
          ? error.response.data.detail
          : "Could not create your account. Please try again.";
      setAlert({ message, tone: "failure" });
    } finally {
      setSubmitting(false);
    }
  }

  // Non-blocking strength readout. The prototype specifies weak-password
  // feedback inline, below the field, and non-blocking until submit.
  const strength = !password
    ? null
    : password.length < 10
      ? { label: "Too short", tone: "var(--warn)", pct: 30 }
      : /[A-Z]/.test(password) && /\d/.test(password) && /[^A-Za-z0-9]/.test(password)
        ? { label: "Strong", tone: "var(--g600)", pct: 100 }
        : { label: "Fair — mix in a capital, a number or a symbol", tone: "var(--ink3)", pct: 65 };

  return (
    <AuthLayout
      title="Create your Scanwick account"
      sub={
        plan
          ? `Free — one account, one analysis a month · ${planLabels[plan]} plan selected`
          : "Free — one account, one analysis a month."
      }
      alert={alert ? <AuthAlert {...alert} /> : undefined}
    >
      <AuthForm onSubmit={form.handleSubmit(onSubmit)}>
        <Controller
          name="fullName"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field label="Full name" id="full-name" error={fieldState.error?.message}>
              <Inp
                id="full-name"
                autoComplete="name"
                placeholder="Adaeze Nwankwo"
                invalid={!!fieldState.error}
                {...field}
              />
            </Field>
          )}
        />

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
          name="phone"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field
              label="Phone number"
              id="phone"
              error={fieldState.error?.message}
              hint="Nigerian formats: 0803…, +234 803…, 234803…"
            >
              <Inp
                id="phone"
                type="tel"
                autoComplete="tel"
                placeholder="0803 000 0000"
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
            <Field
              label="Password"
              id="password"
              error={fieldState.error?.message}
              hint="At least 10 characters."
            >
              <PasswordInput
                id="password"
                name={field.name}
                value={field.value}
                onChange={field.onChange}
                onBlur={field.onBlur}
                autoComplete="new-password"
                placeholder="At least 10 characters"
                invalid={!!fieldState.error}
              />
              {strength ? (
                <div style={{ marginTop: 7 }}>
                  <div className="bar">
                    <i style={{ width: `${strength.pct}%`, background: strength.tone }} />
                  </div>
                  <div className="hint" style={{ color: strength.tone }}>
                    {strength.label}
                  </div>
                </div>
              ) : null}
            </Field>
          )}
        />

        <Controller
          name="consent"
          control={form.control}
          render={({ field, fieldState }) => (
            <>
              <label
                style={{ display: "flex", gap: 9, alignItems: "flex-start", margin: "14px 0", cursor: "pointer" }}
              >
                <input
                  type="checkbox"
                  checked={field.value}
                  onChange={(e) => field.onChange(e.target.checked)}
                  style={{ marginTop: 3 }}
                  aria-invalid={!!fieldState.error}
                />
                <span style={{ fontSize: 12, color: "var(--ink2)", lineHeight: 1.55 }}>
                  I have read and agree to the{" "}
                  <Link to="/terms" style={{ color: "var(--g700)", fontWeight: 600 }}>
                    Terms of Service
                  </Link>{" "}
                  and{" "}
                  <Link to="/privacy" style={{ color: "var(--g700)", fontWeight: 600 }}>
                    Privacy Policy
                  </Link>
                  , and I consent to Scanwick creating an account for me.
                </span>
              </label>
              {fieldState.error ? (
                <div className="errmsg" role="alert" style={{ marginTop: -8, marginBottom: 10 }}>
                  {fieldState.error.message}
                </div>
              ) : null}
            </>
          )}
        />

        <Btn type="submit" block disabled={submitting}>
          {submitting ? "Creating your account…" : "Create account"}
        </Btn>
      </AuthForm>

      <GoogleAuth label="Sign up with Google" />
      <AuthFootLink desc="Already have an account?" link="Sign in" to="/login" />
    </AuthLayout>
  );
}
