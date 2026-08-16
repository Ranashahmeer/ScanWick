import { getCookie, removeCookie, setCookie } from "@/lib/cookies"
import { authStore } from "@/lib/auth-store"

// Access token lives in memory only (cleared on tab close / reload) so it
// never touches any JS-readable persistent storage. The refresh token has
// to be persisted somewhere to survive a reload, and the backend issues it
// in the response body rather than an httpOnly cookie — so a JS-readable
// cookie (SameSite=Strict, Secure on https) is the least-bad option here,
// not a fully XSS-proof one.
const REFRESH_TOKEN_COOKIE = "scanwick_refresh_token"
const REFRESH_TOKEN_MAX_AGE = 60 * 60 * 24 * 7 // 7 days, matches backend refresh_token_expire_days default

// The access token and authStore are both in-memory/per-tab, so logging out
// in one tab otherwise leaves every other open tab working with a session
// whose refresh cookie was just cleared — it keeps "working" until its
// access token naturally expires and its own refresh attempt fails (see
// api-client.ts's refresh-failure handling). Writing a localStorage key on
// logout fires a `storage` event in every *other* tab (same-tab writes don't
// trigger it), so they can clear out immediately instead of limping along on
// dead tokens.
const LOGOUT_BROADCAST_KEY = "scanwick_logout_event"

if (typeof window !== "undefined") {
  window.addEventListener("storage", (event) => {
    if (event.key === LOGOUT_BROADCAST_KEY && event.newValue) {
      accessToken = null
      removeCookie(REFRESH_TOKEN_COOKIE)
      authStore.setUnauthenticated()
    }
  })
}

let accessToken: string | null = null

export function getAccessToken(): string | null {
  return accessToken
}

export function getRefreshToken(): string | null {
  return getCookie(REFRESH_TOKEN_COOKIE) ?? null
}

export function setTokens(tokens: { accessToken: string; refreshToken: string }): void {
  accessToken = tokens.accessToken
  setCookie(REFRESH_TOKEN_COOKIE, tokens.refreshToken, REFRESH_TOKEN_MAX_AGE, {
    sameSite: "Strict",
  })
}

export function setAccessToken(token: string): void {
  accessToken = token
}

export function clearTokens(): void {
  accessToken = null
  removeCookie(REFRESH_TOKEN_COOKIE)
}

export function broadcastLogout(): void {
  try {
    localStorage.setItem(LOGOUT_BROADCAST_KEY, Date.now().toString())
  } catch {
    // Ignore
  }
}

export function logoutUser(): void {
  clearTokens();
  broadcastLogout();
  authStore.setUnauthenticated();
  window.location.href = "/login";
}

