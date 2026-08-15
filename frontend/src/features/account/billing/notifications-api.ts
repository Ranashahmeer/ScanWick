import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { isAxiosError } from "axios"
import { apiClient } from "@/lib/api-client"

export class NotificationsApiError extends Error {}

function errorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.error?.message === "string") {
    return error.response.data.error.message
  }
  return fallback
}

interface Envelope<T> {
  success: boolean
  data: T
}

export interface NotificationPreference {
  event_key: string
  label: string
  email: boolean
  in_app: boolean
  slack: boolean
}

export function useNotificationPreferences() {
  return useQuery({
    queryKey: ["notifications", "preferences"],
    queryFn: async () => {
      const { data } = await apiClient.get<Envelope<NotificationPreference[]>>("/notifications/preferences")
      return data.data
    },
  })
}

export function useSaveNotificationPreferences() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (preferences: NotificationPreference[]) => {
      try {
        await apiClient.put("/notifications/preferences", { preferences })
      } catch (error) {
        throw new NotificationsApiError(errorMessage(error, "Could not save your preferences. Please try again."))
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications", "preferences"] })
    },
  })
}
