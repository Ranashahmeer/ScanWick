import { useMutation } from "@tanstack/react-query"
import { isAxiosError } from "axios"
import { authClient } from "@/lib/api-client"
import { authStore, type AuthUser } from "@/lib/auth-store"

export class ProfileApiError extends Error {}

function errorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.detail === "string") {
    return error.response.data.detail
  }
  return fallback
}

export interface UpdateProfileInput {
  first_name?: string
  last_name?: string
  company?: string
  company_size?: string
  industry?: string
  primary_currency?: string
  language?: string
  timezone?: string
}

export function useUpdateProfile() {
  return useMutation({
    mutationFn: async (input: UpdateProfileInput) => {
      try {
        const { data } = await authClient.patch<AuthUser>("/me", input)
        return data
      } catch (error) {
        throw new ProfileApiError(errorMessage(error, "Could not save your changes. Please try again."))
      }
    },
    onSuccess: (user) => {
      authStore.setAuthenticated(user)
    },
  })
}

export function useUploadAvatar() {
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append("file", file)
      try {
        const { data } = await authClient.post<AuthUser>("/me/avatar", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        })
        return data
      } catch (error) {
        throw new ProfileApiError(errorMessage(error, "Could not upload your photo. Please try again."))
      }
    },
    onSuccess: (user) => {
      authStore.setAuthenticated(user)
    },
  })
}
