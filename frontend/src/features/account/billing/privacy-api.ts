import { useMutation, useQueryClient } from "@tanstack/react-query"
import { isAxiosError } from "axios"
import { apiClient, authClient } from "@/lib/api-client"
import { authStore, type AuthUser } from "@/lib/auth-store"

export class PrivacyApiError extends Error {}

function errorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.error?.message === "string") {
    return error.response.data.error.message
  }
  if (isAxiosError(error) && typeof error.response?.data?.detail === "string") {
    return error.response.data.detail
  }
  return fallback
}

export function useDeleteAllData() {
  return useMutation({
    mutationFn: async () => {
      try {
        await apiClient.post("/privacy/delete-data")
      } catch (error) {
        throw new PrivacyApiError(errorMessage(error, "Could not delete your data. Please try again."))
      }
    },
  })
}

export function useDeleteAccount() {
  return useMutation({
    mutationFn: async () => {
      try {
        await authClient.post("/delete-account")
      } catch (error) {
        throw new PrivacyApiError(errorMessage(error, "Could not schedule account deletion. Please try again."))
      }
      // /delete-account only returns a message, not the fresh user row —
      // re-fetch /me so authStore's deletion_requested_at reflects it
      // immediately (the access token itself is still valid; only refresh
      // tokens were revoked server-side).
      const { data } = await authClient.get<AuthUser>("/me")
      authStore.setAuthenticated(data)
      return data
    },
  })
}

export function useCancelDeleteAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      try {
        await authClient.post("/delete-account/cancel")
      } catch (error) {
        throw new PrivacyApiError(errorMessage(error, "Could not cancel account deletion. Please try again."))
      }
    },
    onSuccess: async () => {
      // Both delete-account endpoints only return a message, not the fresh
      // user row — re-fetch /me directly so authStore's cached
      // deletion_requested_at clears immediately instead of waiting for
      // some unrelated refetch to happen to occur.
      const { data } = await authClient.get<AuthUser>("/me")
      authStore.setAuthenticated(data)
      queryClient.invalidateQueries()
    },
  })
}

export async function downloadDataExport(): Promise<void> {
  const response = await apiClient.get("/privacy/export", { responseType: "blob" })
  const url = URL.createObjectURL(response.data as Blob)
  const link = document.createElement("a")
  link.href = url
  link.download = "scanwick-data-export.json"
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
