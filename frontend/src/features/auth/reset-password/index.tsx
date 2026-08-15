import { zodResolver } from "@hookform/resolvers/zod"
import { Controller, useForm } from "react-hook-form"
import * as z from "zod"
import { useNavigate } from "@tanstack/react-router"
import { isAxiosError } from "axios"
import FormField from "@/components/FormField"
import CardLayout from "./components/CardLayout"
import AlertBox from "@/components/AlertBox"
import { useState, useEffect } from "react"
import { authClient } from "@/lib/api-client"

function errorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.detail === "string") {
    return error.response.data.detail
  }
  return fallback
}

function EmailCard () {

    const [alertMessage, setAlertMessage] = useState(<></>)
    const [submitting, setSubmitting] = useState(false)

    const formSchema = z.object({
        email: z
        .email("Email is required in format xyz@example.com"),
    })


    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
        email: ""
        },
    })

    const errors = form.formState.errors;

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


    const inputFields = (
        <div>
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
        </div>
    )

    async function onSubmit(data: z.infer<typeof formSchema>) {
        if (submitting) return
        setSubmitting(true)

        try {
            const response = await authClient.post("/forgot-password", { email: data.email })
            // Backend now discloses account state explicitly (not registered /
            // not verified / sent) — show its actual message rather than a
            // hardcoded one.
            setAlertMessage(
                <AlertBox message={response.data?.message ?? "A password reset link has been sent to your email."} messageType="success" />
            )
        } catch (error) {
            setAlertMessage(<AlertBox message={errorMessage(error, "Something went wrong. Please try again.")} messageType="failure" />)
        } finally {
            setSubmitting(false)
        }
    }

    return(
        <CardLayout
            title="Reset Password"
            desc="Enter your email to get a password reset link"
            inputFields={inputFields}
            buttonText="Send Reset Link"
            footerDesc="Remember your password?"
            linkPath="/login"
            link="Back to Sign in"
            form={form}
            onSubmit={onSubmit}
            alertMessage={alertMessage}
        />
    )
}

type ResetCardProps = {
    token: string
}

function ResetCard ({ token }: ResetCardProps) {

    const navigate = useNavigate()
    const [alertMessage, setAlertMessage] = useState(<></>);
    const [submitting, setSubmitting] = useState(false)

    const formSchema = z.object({
        password: z
        .string("Password is required")
        .nonempty("Password is required")
        .min(8, "Password must be at least 8 character"),
        confirmPassword: z
        .string()
        .nonempty("Confirm the password by re typing it")
    })


    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
        password: "",
        confirmPassword: ""
        },
    })

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


  async function onSubmit(data: z.infer<typeof formSchema>) {
    if (submitting) return

    if (data.password !== data.confirmPassword)
    {
        setAlertMessage(
            <AlertBox
            message="Password mismatched"
            messageType='failure'
            />
        )
        return;
    }

    setSubmitting(true)
    try {
        await authClient.post("/reset-password", { token, new_password: data.password })
        setAlertMessage(<AlertBox message="Password updated. Please log in again." messageType='success' />)
        navigate({ to: "/login" })
    } catch (error) {
        setAlertMessage(<AlertBox message={errorMessage(error, "Reset link is invalid or has expired.")} messageType='failure' />)
    } finally {
        setSubmitting(false)
    }
  }


    const inputFields = (
        <div className="flex flex-col gap-[24px]">
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
                    placeholder="**************"
                  />
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

    return(
        <CardLayout 
            title="Set New Password"
            desc="Reset your password to continu accessing account"
            inputFields={inputFields}
            buttonText="Update"
            alertMessage={alertMessage}
            form={form}
            onSubmit={onSubmit}
        />
    )
}


export {EmailCard, ResetCard}