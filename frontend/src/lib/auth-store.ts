export interface AuthRole {
  vertical: "bank" | "ecommerce"
  role: string
  rep_id: string | null
}

export interface AuthUser {
  id: number
  first_name: string | null
  last_name: string | null
  email: string
  google_id: string | null
  avatar_url: string | null
  is_verified: boolean
  merchant_id: string | null
  // Every UserMerchantRole row for merchant_id, returned by GET /api/auth/me
  // — lets the team-permissions page (and anything else role-aware) know
  // "what am I allowed to do here" without a second round trip.
  roles: AuthRole[]
  company: string | null
  company_size: string | null
  industry: string | null
  primary_currency: string | null
  language: string | null
  timezone: string | null
  totp_enabled: boolean
  // Set once POST /auth/delete-account has been called, cleared by
  // /delete-account/cancel — the Privacy & Data tab reads this to show a
  // "deletion pending" state instead of the delete button.
  deletion_requested_at: string | null
}

type AuthState =
  | { status: "loading"; user: null }
  | { status: "authenticated"; user: AuthUser }
  | { status: "unauthenticated"; user: null }

let state: AuthState = { status: "loading", user: null }
const listeners = new Set<() => void>()

function setState(next: AuthState): void {
  state = next
  listeners.forEach((listener) => listener())
}

export const authStore = {
  getState: (): AuthState => state,
  setAuthenticated: (user: AuthUser): void => setState({ status: "authenticated", user }),
  setUnauthenticated: (): void => setState({ status: "unauthenticated", user: null }),
  subscribe: (listener: () => void): (() => void) => {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
}
