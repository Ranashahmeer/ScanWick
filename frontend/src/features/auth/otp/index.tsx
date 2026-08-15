import { zodResolver } from "@hookform/resolvers/zod"
import { Controller, useForm } from "react-hook-form"
import * as z from "zod"
import { useState } from "react"
import { useNavigate } from "@tanstack/react-router"
import { isAxiosError } from "axios"

import CardLayout from "@/features/auth/reset-password/components/CardLayout"
import AlertBox from "@/components/AlertBox"
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp"
import { REGEXP_ONLY_DIGITS } from "input-otp"
import { FieldLabel } from "@/components/ui/field"
import { authClient } from "@/lib/api-client"
import { setTokens } from "@/lib/auth-tokens"
import { authStore, type AuthUser } from "@/lib/auth-store"

interface TokenResponse {
  access_token: string
  refresh_token: string
}

type OtpCardProps = {
  email: string
  plan?: "free" | "basic" | "premium"
}

function errorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.detail === "string") {
    return error.response.data.detail
  }
  return fallback
}

export default function OtpCard({ email, plan }: OtpCardProps) {
  const navigate = useNavigate()
  const [alertMessage, setAlertMessage] = useState(<></>)
  const [resending, setResending] = useState(false)

  const formSchema = z.object({
    otp: z
      .string()
      .length(6, "Enter the 6-digit code")
      .regex(/^\d{6}$/, "Code must contain only digits"),
  })

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: { otp: "" },
  })

  async function onSubmit(data: z.infer<typeof formSchema>) {
    try {
      const { data: tokens } = await authClient.post<TokenResponse>("/verify-otp", {
        email,
        otp: data.otp,
        purpose: "verification",
      })
      setTokens({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token })

      // OTP verification itself has already succeeded and tokens are issued
      // at this point — a failure here is NOT an invalid/expired-code
      // problem, so it must not be reported as one.
      try {
        const { data: user } = await authClient.get<AuthUser>("/me")
        authStore.setAuthenticated(user)

        // A paid plan was picked back on the landing page before this
        // account even existed — carry it through to checkout now instead
        // of dropping it and making them find their way to Billing and
        // pick the same plan again. Free needs no checkout at all.
        if (plan === "basic" || plan === "premium") {
          navigate({ to: "/account", search: { tab: "billing", upgrade: plan } })
        } else {
          // Land on Upload, not the dashboard — see login/index.tsx for why.
          navigate({ to: "/upload" })
        }
      } catch {
        setAlertMessage(
          <AlertBox
            message="Signed in, but couldn't load your profile — please try again."
            messageType="failure"
          />
        )
      }
    } catch (error) {
      setAlertMessage(
        <AlertBox message={errorMessage(error, "Invalid or expired code.")} messageType="failure" />
      )
    }
  }

  async function handleResend() {
    if (resending) return
    setResending(true)
    try {
      await authClient.post("/resend-otp", { email, purpose: "verification" })
      setAlertMessage(<AlertBox message="A new code has been sent." messageType="success" />)
    } catch (error) {
      setAlertMessage(
        <AlertBox message={errorMessage(error, "Could not resend the code.")} messageType="failure" />
      )
    } finally {
      setResending(false)
    }
  }

  const inputFields = (
    <div className="w-[100%] flex flex-col items-center gap-[12px]">
      <FieldLabel className="self-start mx-[48px] text-gray-500 text-sm">Enter Code</FieldLabel>
      <Controller
        name="otp"
        control={form.control}
        render={({ field }) => (
          <InputOTP
            maxLength={6}
            value={field.value}
            onChange={field.onChange}
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
        )}
      />
    </div>
  )

  return (
    <CardLayout
      title="Verify Email"
      desc={`Enter the verification code we sent to ${email}`}
      inputFields={inputFields}
      buttonText="Verify"
      footerDesc="Didn't receive the code?"
      link={resending ? "Sending..." : "Resend"}
      onFooterLinkClick={handleResend}
      alertMessage={alertMessage}
      form={form}
      onSubmit={onSubmit}
    />
  )
}
