import { authClient, refreshAccessToken } from "@/lib/api-client"
import { authStore, type AuthUser } from "@/lib/auth-store"
import { clearTokens, getRefreshToken } from "@/lib/auth-tokens"

// The access token only ever lives in memory (see auth-tokens.ts), so a
// fresh page load always starts with none — even when a valid refresh
// token cookie is still around. Restoring a session therefore means
// explicitly refreshing first, then fetching the user, rather than just
// trying `/me` and hoping the request interceptor's 401-triggered refresh
// kicks in (it wouldn't: FastAPI's HTTPBearer returns 403, not 401, when
// no Authorization header is sent at all).
let bootstrapPromise: Promise<void> | null = null

async function bootstrap(): Promise<void> {
  if (!getRefreshToken()) {
    authStore.setUnauthenticated()
    return
  }

  try {
    await refreshAccessToken()
    const { data } = await authClient.get<AuthUser>("/me")
    authStore.setAuthenticated(data)
  } catch {
    clearTokens()
    authStore.setUnauthenticated()
  }
}

// Memoized so every route's beforeLoad can await it without triggering the
// refresh-and-fetch sequence more than once per page load.
export function ensureAuthBootstrapped(): Promise<void> {
  if (!bootstrapPromise) {
    bootstrapPromise = bootstrap()
  }
  return bootstrapPromise
}
