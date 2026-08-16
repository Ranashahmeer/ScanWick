import { zodResolver } from "@hookform/resolvers/zod"
import { Controller, useForm } from "react-hook-form"
import * as z from "zod"
import { useNavigate } from "@tanstack/react-router"
import { isAxiosError } from "axios"

import {
  Card,
  CardContent,
} from "@/components/ui/card"
import {
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"

import { AuthHeader, AuthFooter } from "@/components/auth-card"

import AlertBox from "@/components/AlertBox"
import FormField from "@/components/FormField"
import { useEffect, useState } from "react"
import { authClient } from "@/lib/api-client"

const planLabels = {
  free: "Free",
  basic: "Basic",
  premium: "Premium",
} as const

type RegisterProps = {
  plan?: "free" | "basic" | "premium"
}

export default function Register({ plan }: RegisterProps) {

  const navigate = useNavigate()
  const [alertMessage, setAlertMessage] = useState(<></>)
  const [submitting, setSubmitting] = useState(false)


  const formSchema = z.object({
    firstName: z
      .string()
      .nonempty("First Name is required"),
    lastName: z
      .string()
      .nonempty("Last Name is required"),
    email: z
      .email("Email should be in format xyz@example.com"),
      password: z
        .string("Password is required")
        .nonempty("Password is required")
        .min(8, "Password must be at least 8 character")
  })


  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      firstName: "",
      lastName: "",
      email: "",
      password: ""
    },
  })

  const errors = form.formState.errors

  useEffect(()=>{
    // Extract the first error message from the errors object
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

  

  async function onSubmit(data: z.infer<typeof formSchema>) {
    if (submitting) return
    setSubmitting(true)

    try {
      await authClient.post("/register", {
        first_name: data.firstName,
        last_name: data.lastName,
        email: data.email,
        password: data.password,
      })
      navigate({ to: "/otp", search: { email: data.email, plan } })
    } catch (error) {
      const message = isAxiosError(error) && typeof error.response?.data?.detail === "string"
        ? error.response.data.detail
        : "Could not create your account. Please try again."
      setAlertMessage(<AlertBox message={message} messageType='failure' />)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#F7F9F8] via-[#EDF5F0] to-[#E2F0E7] flex flex-col justify-center items-center px-4 py-12">
      <div className="w-full max-w-md flex flex-col gap-3">
        {alertMessage}

        <Card className="w-full bg-white/95 backdrop-blur-sm border border-[#DCE3DF]/60 shadow-[0_2px_4px_rgba(0,0,0,0.04),0_12px_40px_rgba(0,34,15,0.08)] rounded-2xl p-4 sm:p-6">
          <AuthHeader
            title="Create your account"
            desc={
              plan
                ? `Free — one account, one analysis a month · ${planLabels[plan]} plan selected`
                : "Free — one account, one analysis a month"
            }
          />
        
        <form id="register-form" onSubmit={form.handleSubmit(onSubmit)}>
          <CardContent>
  
            <FieldGroup>
              <div>
                <FieldLabel className="text-gray-500 ml-[4px]">Name</FieldLabel>
                <div className="flex mx-[4px] justify-around gap-[12px] items-center">
                  <Controller 
                    name="firstName"
                    control={form.control}
                    render={({ field, fieldState }) => (
                      <FormField 
                        field={field} 
                        fieldState={fieldState}
                        label=""
                        id="first-name"
                        placeholder="First Name"
                      />
                    )}
                  />
                  <Controller 
                    name="lastName"
                    control={form.control}
                    render={({ field, fieldState }) => (
                      <FormField 
                        field={field} 
                        fieldState={fieldState}
                        label=""
                        id="last-name"
                        placeholder="Last Name"
                      />
                    )}
                  />

                </div>
              </div>
  
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
                  <FormField 
                    field={field}
                    fieldState={fieldState}
                    label="Password"
                    id="password"
                    type="password"
                    placeholder="Create a password"
                  />
                )}
              />
  
          </FieldGroup>
        </CardContent>
        
        <AuthFooter
          buttonText="Create Account"
          separatorText="Or sign up with"
          desc="Already have an account?"
          linkPath="/login"
          link="Sign in"
          submitting={submitting}
        />
      </form>
      </Card>
      </div>
    </div>
  )
}
