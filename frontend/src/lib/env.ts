const DEV_FALLBACK_API_BASE_URL = "http://localhost:8000/api/v1"
const DEV_FALLBACK_AUTH_API_BASE_URL = "http://localhost:8000"

function requireEnv(key: keyof ImportMetaEnv, devFallback: string): string {
  const value = import.meta.env[key]
  if (typeof value === "string" && value.length > 0) {
    return value
  }

  if (import.meta.env.PROD) {
    // A missing/blank required env var in a production build is a config
    // mistake, not something to paper over — silently falling back to
    // localhost would point a deployed app at a URL that can never work,
    // and previously surfaced as a confusing network error deep inside the
    // API client instead of a clear failure at startup.
    const message = `Missing required environment variable ${key} in production build.`
    // eslint-disable-next-line no-console
    console.error(message)
    throw new Error(message)
  }

  return devFallback
}

export const env = {
  apiBaseUrl: requireEnv("VITE_API_BASE_URL", DEV_FALLBACK_API_BASE_URL),
  authApiBaseUrl: requireEnv("VITE_AUTH_API_BASE_URL", DEV_FALLBACK_AUTH_API_BASE_URL),
}
