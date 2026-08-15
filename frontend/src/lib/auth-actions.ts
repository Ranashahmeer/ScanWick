import { authClient } from "@/lib/api-client"
import { authStore } from "@/lib/auth-store"
import { broadcastLogout, clearTokens, getRefreshToken } from "@/lib/auth-tokens"

export async function logout(): Promise<void> {
  const refreshToken = getRefreshToken()

  clearTokens()
  authStore.setUnauthenticated()
  broadcastLogout()

  if (refreshToken) {
    // Best-effort — the session is already cleared client-side regardless
    // of whether the backend call succeeds.
    try {
      await authClient.post("/logout", { refresh_token: refreshToken })
    } catch {
      // Nothing to recover — client-side state is already logged out.
    }
  }
}
