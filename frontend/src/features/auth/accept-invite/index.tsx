import { zodResolver } from "@hookform/resolvers/zod"
import { Controller, useForm } from "react-hook-form"
import * as z from "zod"
import { useNavigate } from "@tanstack/react-router"
import { isAxiosError } from "axios"
import { useState, useEffect } from "react"
import FormField from "@/components/FormField"
import AlertBox from "@/components/AlertBox"
import CardLayout from "@/features/auth/reset-password/components/CardLayout"
import { apiClient, authClient } from "@/lib/api-client"
import { setTokens } from "@/lib/auth-tokens"
import { authStore, type AuthUser } from "@/lib/auth-store"
import { useAuth } from "@/hooks/use-auth"

function errorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.error?.message === "string") {
    return error.response.data.error.message
  }
  return fallback
}

interface AcceptInviteResponse {
  data: {
    user: { id: number; email: string }
    tokens: { access_token: string; refresh_token: string } | null
  }
}

async function refreshSessionAndGoToUpload(navigate: ReturnType<typeof useNavigate>) {
  const { data: user } = await authClient.get<AuthUser>("/me")
  authStore.setAuthenticated(user)
  navigate({ to: "/upload" })
}

interface AcceptInvitePageProps {
  token: string
}

export function AcceptInvitePage({ token }: AcceptInvitePageProps) {
  const { status, user } = useAuth()

  if (status === "loading") {
    return (
      <div className="h-screen flex items-center justify-center">
        <p className="text-slate-500">Checking your session…</p>
      </div>
    )
  }

  if (status === "authenticated" && user) {
    return <ExistingAccountAccept token={token} email={user.email} />
  }

  return <NewAccountAccept token={token} />
}

function ExistingAccountAccept({ token, email }: { token: string; email: string }) {
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)
  const [alertMessage, setAlertMessage] = useState(<></>)

  async function handleAccept() {
    if (submitting) return
    setSubmitting(true)
    try {
      await apiClient.post(`/team/invite/${token}/accept`, {})
      await refreshSessionAndGoToUpload(navigate)
    } catch (error) {
      setAlertMessage(
        <AlertBox
          message={errorMessage(error, "This invite link is invalid, expired, or already used.")}
          messageType="failure"
        />
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="h-screen flex flex-col justify-center items-center gap-[24px]">
      <div className="w-sm sm:max-w-md flex flex-col gap-[8px]">{alertMessage}</div>
      <div className="w-[482px] flex flex-col gap-[16px] items-center rounded-lg border border-slate-200 p-[32px] text-center">
        <h1 className="text-lg font-semibold">Accept team invite</h1>
        <p className="text-sm text-slate-500">
          You're signed in as <strong>{email}</strong>. Accept this invite to get access to the team that invited
          you.
        </p>
        <button
          type="button"
          disabled={submitting}
          onClick={handleAccept}
          className="w-[264px] rounded-[5px] bg-primary text-primary-foreground shadow-[0_8px_20px_rgba(0,34,15,0.18)] py-2 transition-transform hover:-translate-y-0.5 hover:bg-primary/90"
        >
          {submitting ? "Accepting…" : "Accept invite"}
        </button>
      </div>
    </div>
  )
}

function NewAccountAccept({ token }: { token: string }) {
  const navigate = useNavigate()
  const [alertMessage, setAlertMessage] = useState(<></>)
  const [submitting, setSubmitting] = useState(false)

  const formSchema = z
    .object({
      firstName: z.string().nonempty("First name is required"),
      lastName: z.string().nonempty("Last name is required"),
      password: z.string().min(8, "Password must be at least 8 characters"),
      confirmPassword: z.string().nonempty("Confirm your password"),
    })
    .refine((data) => data.password === data.confirmPassword, {
      message: "Passwords don't match",
      path: ["confirmPassword"],
    })

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: { firstName: "", lastName: "", password: "", confirmPassword: "" },
  })

  const errors = form.formState.errors

  useEffect(() => {
    const firstError = Object.values(errors).find((error) => error && error.message) as
      | { message: string }
      | undefined
    if (firstError?.message) {
      setAlertMessage(<AlertBox message={firstError.message} messageType="failure" />)
    }
  }, [errors])

  async function onSubmit(data: z.infer<typeof formSchema>) {
    if (submitting) return
    setSubmitting(true)

    try {
      const { data: response } = await apiClient.post<AcceptInviteResponse>(`/team/invite/${token}/accept`, {
        first_name: data.firstName,
        last_name: data.lastName,
        password: data.password,
      })
      if (response.data.tokens) {
        setTokens({
          accessToken: response.data.tokens.access_token,
          refreshToken: response.data.tokens.refresh_token,
        })
      }
      await refreshSessionAndGoToUpload(navigate)
    } catch (error) {
      setAlertMessage(
        <AlertBox
          message={errorMessage(error, "This invite link is invalid, expired, or already used.")}
          messageType="failure"
        />
      )
    } finally {
      setSubmitting(false)
    }
  }

  const inputFields = (
    <div className="flex flex-col gap-[16px]">
      <Controller
        name="firstName"
        control={form.control}
        render={({ field, fieldState }) => (
          <FormField field={field} fieldState={fieldState} label="First name" id="first-name" type="text" placeholder="Ada" />
        )}
      />
      <Controller
        name="lastName"
        control={form.control}
        render={({ field, fieldState }) => (
          <FormField field={field} fieldState={fieldState} label="Last name" id="last-name" type="text" placeholder="Okafor" />
        )}
      />
      <Controller
        name="password"
        control={form.control}
        render={({ field, fieldState }) => (
          <FormField field={field} fieldState={fieldState} label="Password" id="password" type="password" placeholder="**************" />
        )}
      />
      <Controller
        name="confirmPassword"
        control={form.control}
        render={({ field, fieldState }) => (
          <FormField
            field={field}
            fieldState={fieldState}
            label="Confirm Password"
            id="confirm-password"
            type="password"
            placeholder="**************"
          />
        )}
      />
    </div>
  )

  return (
    <CardLayout
      title="Accept your team invite"
      desc="Create your account to accept the invite and get access."
      inputFields={inputFields}
      buttonText={submitting ? "Creating account…" : "Accept & create account"}
      alertMessage={alertMessage}
      form={form}
      onSubmit={onSubmit}
    />
  )
}
