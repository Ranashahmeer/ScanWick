import axios, { type AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from "axios"

import { env } from "@/lib/env"
import { handleServerError } from "@/lib/handle-server-error"
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/lib/auth-tokens"
import { authStore } from "@/lib/auth-store"

declare module "axios" {
  interface InternalAxiosRequestConfig {
    _retriedAfterRefresh?: boolean
  }
}

interface RefreshResponse {
  access_token: string
  refresh_token: string
}

// The backend rotates the refresh token on every use (old one is deleted
// server-side as soon as it's redeemed). If several requests 401 at once
// (e.g. a dashboard firing parallel queries when the access token expires),
// each must NOT call /refresh independently — the second call would submit
// a refresh token the first call already consumed and get rejected, logging
// the user out even though the first refresh succeeded. Sharing one in-flight
// promise coalesces concurrent 401s into a single /refresh call.
let refreshPromise: Promise<string> | null = null

export async function refreshAccessToken(): Promise<string> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const refreshToken = getRefreshToken()
      if (!refreshToken) {
        throw new Error("No refresh token available")
      }
      // Plain axios, not `client` — this must never go through these same
      // interceptors, or a failed refresh would recurse forever.
      const { data } = await axios.post<RefreshResponse>(
        `${env.authApiBaseUrl}/api/auth/refresh`,
        { refresh_token: refreshToken }
      )
      setTokens({ accessToken: data.access_token, refreshToken: data.refresh_token })
      return data.access_token
    })().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

function createClient(baseURL: string): AxiosInstance {
  const client = axios.create({ baseURL })

  client.interceptors.request.use((config) => {
    const token = getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  client.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const originalRequest = error.config as InternalAxiosRequestConfig | undefined
      const isUnauthorized = error.response?.status === 401

      if (isUnauthorized && originalRequest && !originalRequest._retriedAfterRefresh) {
        originalRequest._retriedAfterRefresh = true
        try {
          const accessToken = await refreshAccessToken()
          originalRequest.headers.Authorization = `Bearer ${accessToken}`
          return client(originalRequest)
        } catch {
          clearTokens()
          authStore.setUnauthenticated()
        }
      }

      handleServerError(error)
      return Promise.reject(error)
    }
  )

  return client
}

// /api/v1/* — ecommerce, bank, reconciliation, uploads, analyze
export const apiClient = createClient(env.apiBaseUrl)

// /api/auth/* — lives directly under the API root, not under /api/v1
export const authClient = createClient(`${env.authApiBaseUrl}/api/auth`)
