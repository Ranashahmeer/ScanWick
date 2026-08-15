import { useSyncExternalStore } from "react"
import { authStore } from "@/lib/auth-store"

export function useAuth() {
  return useSyncExternalStore(authStore.subscribe, authStore.getState)
}
