import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { isAxiosError } from "axios"
import { authClient } from "@/lib/api-client"

export class SecurityApiError extends Error {}

function errorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.detail === "string") {
    return error.response.data.detail
  }
  return fallback
}

// ---- Password ----
export function useChangePassword() {
  return useMutation({
    mutationFn: async (input: { current_password: string; new_password: string }) => {
      try {
        await authClient.post("/change-password", input)
      } catch (error) {
        throw new SecurityApiError(errorMessage(error, "Could not update your password. Please try again."))
      }
    },
  })
}

// ---- Sessions ----
export interface Session {
  id: number
  device: string | null
  ip_address: string | null
  last_used_at: string | null
  created_at: string | null
  is_current: boolean
}

export function useSessions() {
  return useQuery({
    queryKey: ["security", "sessions"],
    queryFn: async () => {
      const { data } = await authClient.get<Session[]>("/sessions")
      return data
    },
  })
}

export function useRevokeSession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (sessionId: number) => {
      try {
        await authClient.delete(`/sessions/${sessionId}`)
      } catch (error) {
        throw new SecurityApiError(errorMessage(error, "Could not revoke that session. Please try again."))
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["security", "sessions"] })
    },
  })
}

// ---- Login history ----
export interface LoginEvent {
  id: string
  when: string
  device: string | null
  ip_address: string | null
  result: "success" | "blocked"
  reason: string | null
}

export function useLoginHistory() {
  return useQuery({
    queryKey: ["security", "login-history"],
    queryFn: async () => {
      const { data } = await authClient.get<LoginEvent[]>("/login-history")
      return data
    },
  })
}

// ---- Two-factor authentication ----
export interface TwoFactorSetup {
  secret: string
  qr_code_base64: string
}

export function useSetup2fa() {
  return useMutation({
    mutationFn: async () => {
      try {
        const { data } = await authClient.post<TwoFactorSetup>("/2fa/setup")
        return data
      } catch (error) {
        throw new SecurityApiError(errorMessage(error, "Could not start two-factor setup. Please try again."))
      }
    },
  })
}

export function useEnable2fa() {
  return useMutation({
    mutationFn: async (code: string) => {
      try {
        await authClient.post("/2fa/enable", { code })
      } catch (error) {
        throw new SecurityApiError(errorMessage(error, "Invalid code. Please try again."))
      }
    },
  })
}

export function useDisable2fa() {
  return useMutation({
    mutationFn: async (currentPassword: string) => {
      try {
        await authClient.post("/2fa/disable", { current_password: currentPassword })
      } catch (error) {
        throw new SecurityApiError(errorMessage(error, "Could not disable two-factor authentication."))
      }
    },
  })
}
