import { zodResolver } from "@hookform/resolvers/zod"
import { Controller, useForm } from "react-hook-form"
import * as z from "zod"
import { Link, useNavigate } from "@tanstack/react-router"
import { isAxiosError } from "axios"

import {Card, CardContent} from "@/components/ui/card"
import {FieldGroup, FieldLabel} from "@/components/ui/field"
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp"
import { REGEXP_ONLY_DIGITS } from "input-otp"

import { AuthHeader, AuthFooter } from "@/components/auth-card"

import AlertBox from "@/components/AlertBox"
import FormField from "@/components/FormField"
import { useState, useEffect } from "react"
import { authClient } from "@/lib/api-client"
import { setTokens } from "@/lib/auth-tokens"
import { authStore, type AuthUser } from "@/lib/auth-store"

interface TokenResponse {
  access_token: string
  refresh_token: string
}

interface LoginResponse {
  access_token?: string
  refresh_token?: string
  message?: string
  email?: string
}

type LoginProps = {
  redirectTo?: string
}

export default function Login({ redirectTo }: LoginProps) {

  const navigate = useNavigate()
  const [alertMessage, setAlertMessage] = useState(<></>)
  const [submitting, setSubmitting] = useState(false)
  // Set once /login responds with {message, email} instead of tokens —
  // meaning the password was correct but the account has TOTP 2FA enabled.
  // Held alongside the password (never sent anywhere except the follow-up
  // /2fa/verify-login call) since that endpoint re-checks it — a correct
  // TOTP code alone must never be enough on its own.
  const [pending2fa, setPending2fa] = useState<{ email: string; password: string } | null>(null)
  const [twoFactorCode, setTwoFactorCode] = useState("")
  const [verifying2fa, setVerifying2fa] = useState(false)

  const formSchema = z.object({
    email: z
      .string()
      .email("Email (xyz@example.com) is required"),
      password: z
        .string()
        .nonempty('Password is required')
  })


  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const errors = form.formState.errors

  useEffect(()=>{

    const firstError = Object.values(errors).find(
      (error) => error && error.message
    ) as { message: string } | undefined

    firstError?.message &&
    setAlertMessage(
        <AlertBox
            message={firstError.message}
            messageType='failure'
          />
    )

  }, [errors])

  async function completeLogin(accessToken: string, refreshToken: string) {
    setTokens({ accessToken, refreshToken })

    // Login itself has already succeeded and tokens are issued at this
    // point — a failure here is NOT a credentials problem, so it must not
    // be reported as one (and must not fall into the caller's catch block,
    // which assumes an invalid-credentials failure).
    try {
      const { data: user } = await authClient.get<AuthUser>("/me")
      authStore.setAuthenticated(user)

      // Land on Upload by default, not the dashboard — the dashboard only
      // makes sense once there's real analysis to show. redirectTo (set
      // when /_app's guard bounced an unauthenticated visit) still wins,
      // so a direct link to e.g. /dashboard behaves as expected.
      navigate({ to: redirectTo || "/upload" })
    } catch {
      setAlertMessage(
        <AlertBox
          message="Signed in, but couldn't load your profile — please try again."
          messageType='failure'
        />
      )
    }
  }

  async function onSubmit(data: z.infer<typeof formSchema>) {
    if (submitting) return
    setSubmitting(true)

    try {
      const { data: result } = await authClient.post<LoginResponse>("/login", data)

      if (!result.access_token || !result.refresh_token) {
        // Password was correct but the account has 2FA enabled — /login
        // returns {message, email} instead of tokens in that case.
        setPending2fa({ email: data.email, password: data.password })
        return
      }

      await completeLogin(result.access_token, result.refresh_token)
    } catch (error) {
      if (isAxiosError(error) && error.response?.status === 403) {
        // Account exists but hasn't completed email verification yet.
        navigate({ to: "/otp", search: { email: data.email } })
        return
      }

      const message = isAxiosError(error) && typeof error.response?.data?.detail === "string"
        ? error.response.data.detail
        : "Invalid email or password."
      setAlertMessage(<AlertBox message={message} messageType='failure' />)
    } finally {
      setSubmitting(false)
    }
  }

  async function onSubmit2fa() {
    if (!pending2fa || verifying2fa) return
    setVerifying2fa(true)

    try {
      const { data: tokens } = await authClient.post<TokenResponse>("/2fa/verify-login", {
        email: pending2fa.email,
        password: pending2fa.password,
        code: twoFactorCode,
      })
      await completeLogin(tokens.access_token, tokens.refresh_token)
    } catch (error) {
      const message = isAxiosError(error) && typeof error.response?.data?.detail === "string"
        ? error.response.data.detail
        : "Invalid two-factor code."
      setAlertMessage(<AlertBox message={message} messageType='failure' />)
    } finally {
      setVerifying2fa(false)
    }
  }

  if (pending2fa) {
    return (
      <div className="h-screen flex flex-col justify-center items-center gap-[24px]">
        <div className="w-sm sm:max-w-md flex flex-col gap-[8px]">
          {alertMessage}
        </div>

        <Card className="w-full sm:max-w-md">
          <AuthHeader
            title="Two-Factor Authentication"
            desc={`Enter the 6-digit code from your authenticator app for ${pending2fa.email}`}
          />

          <CardContent>
            <form
              onSubmit={(event) => {
                event.preventDefault()
                onSubmit2fa()
              }}
            >
              <div className="w-full flex flex-col items-center gap-[12px]">
                <FieldLabel className="self-start mx-[48px] text-gray-500 text-sm">Enter Code</FieldLabel>
                <InputOTP
                  maxLength={6}
                  value={twoFactorCode}
                  onChange={setTwoFactorCode}
                  inputMode="numeric"
                  pattern={REGEXP_ONLY_DIGITS}
                >
                  <InputOTPGroup className="w-[320px] flex justify-center gap-[10px]">
                    <InputOTPSlot index={0} className="size-[44px] rounded-[10px] text-xl border border-gray-200" />
                    <InputOTPSlot index={1} className="size-[44px] rounded-[10px] text-xl border border-gray-200" />
                    <InputOTPSlot index={2} className="size-[44px] rounded-[10px] text-xl border border-gray-200" />
                    <InputOTPSlot index={3} className="size-[44px] rounded-[10px] text-xl border border-gray-200" />
                    <InputOTPSlot index={4} className="size-[44px] rounded-[10px] text-xl border border-gray-200" />
                    <InputOTPSlot index={5} className="size-[44px] rounded-[10px] text-xl border border-gray-200" />
                  </InputOTPGroup>
                </InputOTP>
              </div>

              <AuthFooter
                buttonText="Verify"
                separatorText="Or continue with"
                desc="Wrong account?"
                linkPath="/login"
                link="Back to sign in"
                submitting={verifying2fa}
              />
            </form>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#F7F9F8] via-[#EDF5F0] to-[#E2F0E7] flex flex-col justify-center items-center px-4 py-12">
      <div className="w-full max-w-md flex flex-col gap-3">
        {alertMessage}

        <Card className="w-full bg-white/95 backdrop-blur-sm border border-[#DCE3DF]/60 shadow-[0_2px_4px_rgba(0,0,0,0.04),0_12px_40px_rgba(0,34,15,0.08)] rounded-2xl p-4 sm:p-6">
          <AuthHeader
            title="Welcome back"
            desc="Sign in to your Scanwick account"
          />

        <CardContent>
          <form onSubmit={form.handleSubmit(onSubmit)}>

            <FieldGroup>
              <Controller
                name="email"
                control={form.control}
                render={({ field, fieldState }) => (
                  <FormField
                    field={field}
                    fieldState={fieldState}
                    label="Email"
                    id="email"
                    type="text"
                    placeholder="xyz@example.com"
                  />
                )}
              />

              <Controller
                name="password"
                control={form.control}
                render={({ field, fieldState }) => (
                  <div className="relative">
                    <Link
                      className="absolute right-0 text-xs font-semibold text-[#1b7a4b] hover:text-[#00361c]"
                      to="/getcode"
                    >
                      Forget Password?
                    </Link>
                    <FormField
                      field={field}
                      fieldState={fieldState}
                      label="Password"
                      id="password"
                      type="password"
                      placeholder="Enter your password"
                    />
                  </div>
                )}
              />
            </FieldGroup>

            <AuthFooter
              buttonText="Sign in"
              separatorText="Or continue with"
              desc="New here?"
              linkPath="/register"
              link="Sign up"
              submitting={submitting}
            />
          </form>
        </CardContent>
      </Card>
      </div>
    </div>
  );
}
